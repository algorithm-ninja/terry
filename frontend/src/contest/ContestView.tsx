import React from "react";
import {
  Link, Route, Navigate, useParams, Routes,
} from "react-router-dom";
import { Trans } from "@lingui/macro";
import { LanguageSwitcher } from "src/LanguageSwitcher";
import { Loading } from "src/components/Loading";
import { TaskView } from "src/contest/task/TaskView";
import { PackContextProvider } from "src/admin/PackContext";
import { usePack } from "src/admin/hooks/usePack";
import { ContestData, StartedContest } from "src/types/contest";
import { useCommunicationNotifier } from "src/hooks/useCommunication";
import { LogoutButton } from "src/components/LogoutButton";
import { Error } from "src/components/Error";
import { SidebarView } from "./sidebar/SidebarView";
import {
  useContest,
  useActions,
  ContestContextProvider,
} from "./ContestContext";
import { ContestHome } from "./ContestHome";
import { LoginView } from "./LoginView";
import { useDetectInternet } from "./hooks/useDetectInternet";
import { Communication } from "./Communication";
import { Section } from "./help/Section";

function RenderTask({ contest }: {contest: ContestData}) {
  const { taskName } = useParams() as {taskName: string};
  const startedContest = contest as StartedContest;
  const task = startedContest.contest.tasks.find((t) => t.name === taskName);
  if (!task) {
    return <Trans>Task not found</Trans>;
  }
  return <TaskView task={task} userTask={startedContest.tasks[taskName]} />;
}

function ContestViewInternal() {
  const loadablePack = usePack();
  const contestLoadable = useContest();
  const { logout, isLoggedIn } = useActions();

  useDetectInternet();
  useCommunicationNotifier();

  if (loadablePack.isLoading()) return <Loading />;
  if (loadablePack.isError()) return <Error cause={loadablePack.error()} />;

  const pack = loadablePack.value();
  if (!pack.uploaded) return <Navigate to="/admin" replace />;
  const loggedIn = isLoggedIn();
  if (loggedIn && contestLoadable.isLoading()) return <Loading />;
  const contest = contestLoadable.isReady() ? contestLoadable.value() : null;

  return (
    <>
      <nav className="terry-navbar">
        <Link to="/" className="navbar-brand">
          {contest ? contest.contest.name : "Home"}
        </Link>
        <div className="justify-right" />
        {contest && (
          <span className="terry-user-name">
            {contest.name}
            {" "}
            {contest.surname}
          </span>
        )}
        {contest && <LogoutButton onClick={() => logout()} />}
        <LanguageSwitcher />
      </nav>

      <div className="terry-body">
        <SidebarView />
        <main>
          <Routes>
            {contest && (
              <Route path="/" element={<ContestHome />} />
            )}
            {(!loggedIn || contestLoadable.isError()) && (
              <Route path="/" element={<LoginView />} />
            )}

            {pack.sections?.map((section) => (
              <Route key={section.url} path={`/sections/${section.url}`} element={<Section section={section} />} />
            ))}

            <Route path="/communication/*" element={<Communication />} />

            {contest && contest.contest.has_started && (
              <Route path="/task/:taskName/*" element={<RenderTask contest={contest} />} />
            )}
          </Routes>
        </main>
      </div>
    </>
  );
}

export function ContestView() {
  return (
    <PackContextProvider>
      <ContestContextProvider>
        <ContestViewInternal />
      </ContestContextProvider>
    </PackContextProvider>
  );
}
