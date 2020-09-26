import React from "react";
import { Trans } from "@lingui/macro";
import TaskStatementView from "./TaskStatementView";
import { TaskData, UserTaskData } from "./ContestContext";
import TaskCommands from "./TaskCommands";
import LastSubmission from "./LastSubmission";
import { useStatement } from "./useStatement.hook";

type Props = {
  task: TaskData;
  userTask: UserTaskData;
};

export default function TaskView({ task, userTask }: Props) {
  const statement = useStatement(task.statement_path);

  const renderTaskStatement = () => {
    if (statement.isLoading()) {
      return (
        <p>
          <Trans>Loading...</Trans>
        </p>
      );
    }
    if (statement.isError()) {
      return (
        <p>
          <Trans>Failed to load task statement. Try reloading the page.</Trans>
        </p>
      );
    }
    return <TaskStatementView task={task} source={statement.value()} />;
  };
  return (
    <>
      <h1>{task.title}</h1>
      <TaskCommands task={task} userTask={userTask} />

      {/* <Route
        path="/task/:taskName/submit/:inputId"
        render={({ match }) => (
          <CreateSubmissionView {...this.props} inputId={match.params.inputId} taskName={match.params.taskName} />
        )}
      ></Route> */}
      {/* <Route
        path="/task/:taskName/submissions"
        render={({ match }) => <SubmissionListView {...this.props} taskName={match.params.taskName} />}
      /> */}
      {/* <Route
        path="/task/:taskName/submission/:submissionId"
        render={({ match }) => (
          <SubmissionReportView
            {...this.props}
            submissionId={match.params.submissionId}
            taskName={match.params.taskName}
          />
        )}
      /> */}

      <LastSubmission task={task} userTask={userTask} />

      <hr />

      {renderTaskStatement()}
    </>
  );
}
