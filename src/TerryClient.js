import axios from 'axios';

class Client {
  constructor() {
    this.apiBaseURI = process.env.REACT_APP_API_BASE_URI || "http://localhost:1234/";
    this.api = axios.create({
      baseURL: this.apiBaseURI,
    });

    this.filesBaseURI = process.env.REACT_APP_FILES_BASE_URI || "http://localhost:1235/";
    this.files = axios.create({
      baseURL: this.filesBaseURI,
    });

    this.statementsBaseURI = process.env.REACT_APP_STATEMENTS_BASE_URI || "http://localhost:1234/";
    this.statements = axios.create({
      baseURL: this.statementsBaseURI,
    });
  }
}

export default new Client();
