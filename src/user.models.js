import client from './TerryClient';
import Cookies from 'universal-cookie';
import Observable from './Observable';
import { DateTime, Duration } from 'luxon';
import ObservablePromise from './ObservablePromise';

export class Model extends Observable {
  static cookieName = "userToken";

  constructor() {
    super();

    this.cookies = new Cookies();
    this.inputGenerationPromise = {};
    this.submissions = {};
  }

  onAppStart() {
    if(this.isLoggedIn()) {
      this.refreshUser();
    }
  }

  loadUser(token) {
    return ;
  }

  userToken() {
    return this.cookies.get(Model.cookieName);
  }

  isLoggedIn() {
    return this.userToken() !== undefined;
  }

  serverTime() {
    return DateTime.local().minus(this.timeDelta || {});
  }

  setServerTime(time) {
    this.timeDelta = DateTime.local().diff(time);
  }

  refreshUser() {
    if(!this.isLoggedIn()) throw Error("refreshUser can only be called after a successful login");
    const userToken = this.cookies.get(Model.cookieName);

    this.fireUpdate();
    return this.userStatePromise = new ObservablePromise(
      client.api.get('/user/' + this.userToken())
        .then((response) => {
          this.setServerTime(DateTime.fromHTTP(response.headers['date']));
          delete this.lastLoginAttempt;
          this.fireUpdate();
          return new UserState(this, response.data);
        })
        .catch(error => {
          console.error("Forced logout because: ", error);
          this.logout();
          return Promise.reject(error);
        })
    );
  }

  attemptLogin(token) {
    this.cookies.set(Model.cookieName, token);
    return this.lastLoginAttempt = this.refreshUser();
  }

  logout() {
    if(!this.isLoggedIn()) throw Error("logout() should be called only if logged in");
    this.cookies.remove(Model.cookieName);
    delete this.userStatePromise;
    // TODO redirect to /
    this.fireUpdate();
  }

  getSubmissionPromise(id) {
    if(!id) throw Error();

    if (this.submissions[id] !== undefined) return this.submissions[id];
    return this.submissions[id] = new ObservablePromise(
      client.api.get("/submission/" + id).then((response) => new SubmissionResult(response.data))
    );
  }

}

class SubmissionUploadable {
  constructor(file, submission) {
    this.file = file;
    this.submission = submission;

    this.uploadPromise = new ObservablePromise(this.doUpload());
  }

  doUpload() {
    throw Error("not implemented");
  }

  isValidForSubmit() {
    return this.uploadPromise.isFulfilled();
  }
}

class Output extends SubmissionUploadable {
  doUpload() {
    const data = new FormData();

    data.append("input_id", this.submission.input.id);
    data.append("file", this.file);

    let id;

    return Promise.resolve()
      .then(() => {
        return client.api.post("/upload_output", data).then((response) => {
          id = response.data.id;
          delete this.error;
        });
      })
      .then(() => {
        return client.api.get("/output/" + id);
      });
  }
}

class Source extends SubmissionUploadable {
  doUpload() {
    const data = new FormData();

    data.append("input_id", this.submission.input.id);
    data.append("file", this.file);

    return client.api.post("/upload_source", data)
  }
}

class UserState extends Observable {
  constructor(model, data) {
    super();
    this.model = model;
    this.data = data;

    this.userTaskState = {};
    for(const task of data.contest.tasks) {
      const state = new UserTaskState(this.model, this, task);
      this.userTaskState[task.name] = state;
    }

    this.tasks = this.data.contest.tasks.map((d) => new Task(this, d.name, d));
  }

  getTask(taskName) {
    const byName = {};
    for(let task of this.tasks) {
      byName[task.name] = task;
    }
    return byName[taskName];
  }

  getTaskState(taskName) {
    return this.userTaskState[taskName];
  }

}

class Task extends Observable {
  constructor(contest, name, data) {
    super();

    this.contest = contest;
    this.name = name;
    this.data = data;

    this.statementPromise = new ObservablePromise(
      client.statements.get(this.data.statement_path).then((response) => response.data)
    );
  }
}

class UserTaskState extends Observable {
  constructor(model, user, task) {
    super();

    this.model = model;
    this.user = user;
    this.task = task;

    this.refreshSubmissionList();
  }

  doGetCurrentInput() {
    return this.user.data.tasks[this.task.name].current_input;
  }

  hasCurrentInput() {
    return this.doGetCurrentInput() !== null;
  }

  getCurrentInput() {
    if(!this.hasCurrentInput()) throw new Error();
    return this.doGetCurrentInput();
  }

  isGeneratingInput() {
    return this.inputGenerationPromise !== undefined;
  }

  generateInput() {
    if(this.isGeneratingInput()) throw new Error("already generating input");

    const data = new FormData();

    data.append("token", this.user.data.token);
    data.append("task", this.task.name);

    this.fireUpdate();

    return this.inputGenerationPromise = client.api.post('/generate_input', data).then((response) => {
      return this.model.refreshUser();
    }).then(() => {
      delete this.inputGenerationPromise;
      this.fireUpdate();
    }, (response) => {
      delete this.inputGenerationPromise;
      this.fireUpdate();
      return Promise.reject(response);
    });
  }

  canSubmit(inputId) {
    return this.hasCurrentInput() && this.getCurrentInput().id === inputId;
  }

  createSubmission(inputId) {
    if(!this.canSubmit(inputId)) throw new Error();

    const input = this.getCurrentInput();
    return new Submission(input, this);
  }

  loadSubmissionList() {
    return client.api.get("/user/" + this.user.data.token + "/submissions/" + this.task.name).then((response) => {
      return response.data;
    });
  }

  refreshSubmissionList() {
    this.submissionListPromise = new ObservablePromise(this.loadSubmissionList());
    this.fireUpdate();
  }

}

class Submission extends Observable {
  constructor(input, taskState) {
    super();

    this.input = input;
    this.taskState = taskState;

    this.model = taskState.model;
    this.submitPromise = null;
  }

  setSource(file) {
    if(this.isSubmitted()) throw Error();
    if(this.hasSource()) throw Error("setSource called when hasSource is true");

    this.source = new Source(file, this);
    this.source.uploadPromise.pushObserver(this);
    this.fireUpdate();
  }

  getSource() {
    return this.source;
  }

  hasSource() {
    return this.source !== undefined;
  }

  resetSource() {
    if(this.isSubmitted()) throw Error();
    this.source.uploadPromise.popObserver(this);
    delete this.source;
    this.fireUpdate();
  }

  setOutput(file) {
    if(this.isSubmitted()) throw Error();
    if(this.hasOutput()) throw Error("setOutput called when hasOutput is true")

    this.output = new Output(file, this);
    this.output.uploadPromise.pushObserver(this);
    this.fireUpdate();
  }

  getOutput() {
    return this.output;
  }

  hasOutput() {
    return this.output !== undefined;
  }

  resetOutput() {
    if(this.isSubmitted()) throw Error();
    this.output.uploadPromise.popObserver(this);
    delete this.output;
    this.fireUpdate();
  }

  canSubmit() {
    return !this.isSubmitted() && this.hasOutput() && this.getOutput().isValidForSubmit()
      && this.hasSource() && this.getSource().isValidForSubmit();
  }

  isSubmitted() {
    return this.submitPromise !== null;
  }

  submit() {
    if(!this.canSubmit()) throw new Error("called submit() but canSubmit() returns false");

    const data = new FormData();

    data.append("input_id", this.input.id);
    data.append("source_id", this.getSource().uploadPromise.value.data.id);
    data.append("output_id", this.getOutput().uploadPromise.value.data.id);

    this.fireUpdate();

    return this.submitPromise = new ObservablePromise(
      client.api.post("/submit", data)
      .then((response) => new SubmissionResult(response.data))
      .then((result) => {
        this.model.refreshUser();
        this.taskState.refreshSubmissionList();
        return result;
      })
    );
  }
}

class SubmissionResult extends Observable {
  constructor(data) {
    super();
    if(!data) throw Error();
    this.data = data;
  }
}
