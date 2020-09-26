import "bootstrap/dist/css/bootstrap.min.css";
import "./index.css";
import "./i18n.css";
import "babel-polyfill";

import * as React from "react";
import * as ReactDOM from "react-dom";
import { BrowserRouter as Router, Route, Switch } from "react-router-dom";
import { ToastContainer } from "react-toastify";
import AppView from "./AppView";
import Loading from "./Loading";

import { TransProvider } from "./i18n";

import PackView from "./admin/PackView";

import "react-toastify/dist/ReactToastify.min.css";

/** ****** DEVELOPMENT SPECIFIC ********* */
if (window.location.origin.endsWith(":3000")) window.location.replace("http://localhost:9000");
/** ****** DEVELOPMENT SPECIFIC ********* */

// handle errors in promises
window.addEventListener("unhandledrejection", (event: PromiseRejectionEvent) => {
  // FIXME: dirty trick to avoid alerts in development
  if (!window.location.origin.endsWith(":9000")) {
    // eslint-disable-next-line no-alert
    window.alert(`An error occurred. Please reload the page. (${event.reason || "<no reason>"})`);
  }
});

ReactDOM.render(
  <>
    <TransProvider>
      <React.Suspense fallback={<Loading />}>
        <ToastContainer />
        <Router>
          <Switch>
            <Route path="/admin" component={PackView} />
            <Route component={AppView} />
          </Switch>
        </Router>
      </React.Suspense>
    </TransProvider>
  </>,
  document.getElementById("root"),
);
