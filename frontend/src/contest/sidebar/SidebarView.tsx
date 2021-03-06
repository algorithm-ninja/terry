import React from "react";
import { DateTime } from "luxon";
import { Trans } from "@lingui/macro";
import { NavLink } from "react-router-dom";
import { Countdown } from "src/components/Countdown";
import { TaskData, StartedContest } from "src/types/contest";
import { client } from "src/TerryClient";
import { useContest, useServerTime, useActions } from "src/contest/ContestContext";
import { ScoreView } from "src/contest/ScoreView";
import { NavbarItemView } from "./NavbarItemView";
import "./SidebarView.css";
import { ExtraSections } from "./ExtraSections";

export function SidebarView() {
  const contestL = useContest();
  const serverTime = useServerTime();
  const { isLoggedIn } = useActions();
  const contest = contestL.isReady() ? contestL.value() : null;

  const renderStarted = (startedContest: StartedContest) => (
    <>
      <li className="nav-item title">
        <h5 className="text-uppercase">
          <Trans>Your score</Trans>
        </h5>
        <ScoreView
          style={{ textAlign: "right", marginRight: "1rem" }}
          score={startedContest.total_score}
          max={startedContest.contest.max_total_score}
          size={2}
        />
      </li>

      <li className="divider-vertical" />

      <li className="nav-item title">
        <h5 className="text-uppercase">
          <Trans>Remaining time</Trans>
        </h5>
        <p className="terry-remaining-time">
          <Countdown
            clock={() => serverTime()}
            end={DateTime.fromISO(startedContest.end_time, { zone: "utc" })}
            afterEnd={() => (
              <span>
                <Trans>The contest is finished</Trans>
              </span>
            )}
          />
        </p>
      </li>
      <li className="divider-vertical" />

      <li className="nav-item title">
        <h5 className="text-uppercase">
          <Trans>Tasks</Trans>
        </h5>
      </li>
      <li className="divider-vertical" />

      {startedContest.contest.tasks.map((task: TaskData) => (
        <NavbarItemView key={task.name} taskName={task.name} />
      ))}

      <li className="divider-vertical" />
    </>
  );

  return (
    <nav className="bg-light sidebar">
      <ul className="nav nav-pills flex-column">
        {contest && contest.contest.has_started && renderStarted(contest as StartedContest)}
        {!isLoggedIn() && (
          <li className="nav-item">
            <NavLink exact to="/" className="nav-link tasklist-item" activeClassName="active">
              <Trans>Login</Trans>
            </NavLink>
          </li>
        )}

        {
          client.communications && (
            <>
              <li className="nav-item title mt-3">
                <h5 className="text-uppercase">
                  <Trans>Communication</Trans>
                </h5>
              </li>
              <li className="nav-item">
                <NavLink to="/communication" className="nav-link tasklist-item" activeClassName="active">
                  <Trans>Questions and Announcements</Trans>
                </NavLink>
              </li>
            </>
          )
        }

        <ExtraSections />
      </ul>
    </nav>
  );
}
