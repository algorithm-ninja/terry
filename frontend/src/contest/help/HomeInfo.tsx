import React from "react";
import { Trans } from "@lingui/macro";
import { FontAwesomeIcon } from "@fortawesome/react-fontawesome";
import { faClock } from "@fortawesome/free-solid-svg-icons";

type Props = {
  hasStarted: boolean;
};

export function HomeInfo({ hasStarted }: Props) {
  return hasStarted ? (
    <>
      <h2>
        <Trans>Usage guide</Trans>
      </h2>
      <p>
        <Trans>On the left side of this page you can find the tasks, click on any one to open it.</Trans>
      </p>
      <Trans>
        You can submit
        {" "}
        <em>as many times as you want</em>
        , but you will have a different input every time. When you make
        a submission remember to send the correct source file and the output corresponding to the last generated input.
        When you have uploaded your files
        {" "}
        <em>remember to submit</em>
        {" "}
        them by clicking the green button!
      </Trans>
      <p>
        <Trans>If you want to submit more than one source code file, please create a zip file containing them.</Trans>
      </p>
    </>
  ) : (
    <>
      <div className="jumbotron">
        <h1 className="text-center display-1">
          <FontAwesomeIcon icon={faClock} />
        </h1>
        <p className="text-center">
          <Trans>
            The contest has not started yet! Refresh this page when the contest has started to be able to login.
          </Trans>
        </p>
      </div>
    </>
  );
}
