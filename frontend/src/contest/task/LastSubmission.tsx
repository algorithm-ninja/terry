import React from "react";
import { Trans } from "@lingui/macro";
import { Link } from "react-router-dom";
import { DateTime } from "luxon";
import { RelativeDate } from "src/components/RelativeDate";
import { useServerTime } from "src/contest/ContestContext";
import { Submission, TaskData } from "src/types/contest";

type Props = {
  task: TaskData;
  submissions: Submission[];
};

export function LastSubmission({ task, submissions }: Props) {
  const serverTime = useServerTime();

  if (submissions.length === 0) {
    return null;
  }
  const submission = submissions[submissions.length - 1];
  return (
    <div>
      <strong>
        <Trans>Last submission:</Trans>
      </strong>
      {" "}
      <RelativeDate clock={() => serverTime()} date={DateTime.fromISO(submission.date, { zone: "utc" })} />
      {" "}
      (
      <Link to={`/task/${task.name}/submissions`}>
        <Trans>view all submissions</Trans>
      </Link>
      )
    </div>
  );
}
