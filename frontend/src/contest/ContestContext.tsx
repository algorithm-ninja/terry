import React, {
  ReactNode, useState, createContext, useContext, useMemo, useEffect, useCallback,
} from "react";
import { Duration, DateTime } from "luxon";
import { useNavigate } from "react-router-dom";
import { useLogin } from "src/hooks/useLogin";
import { Loadable } from "src/Loadable";
import { client } from "src/TerryClient";
import { useTriggerUpdate } from "src/hooks/useTriggerUpdate";
import { ContestData } from "src/types/contest";
import { CommunicationContextProvider } from "src/hooks/useCommunication";
import { SubmissionListContextProvider } from "./hooks/useSubmissionList";

export type ContextData = {
  token: string | null;
  serverTimeSkew: Loadable<Duration>;
  contest: Loadable<ContestData>;
};

export type ContextActions = {
  isLoggedIn: () => boolean;
  login: (token: string) => void;
  logout: () => void;
  reloadContest: () => void;
};

type ContestContextType = {
  data: ContextData;
  actions: ContextActions;
};

export const ContestContext = createContext<ContestContextType>({
  data: {
    token: null,
    serverTimeSkew: Loadable.loading(),
    contest: Loadable.loading(),
  },
  actions: {
    isLoggedIn: () => false,
    login: () => {},
    logout: () => {},
    reloadContest: () => {},
  },
});

type ContestContextProps = {
  children: ReactNode;
};

export function ContestContextProvider({ children }: ContestContextProps) {
  const cookieName = "userToken";
  const [token, login, doLogout] = useLogin(cookieName);
  const [serverTimeSkew, setServerTimeSkew] = useState<Loadable<Duration>>(Loadable.loading());
  const [contest, setContest] = useState<Loadable<ContestData>>(Loadable.loading());
  const [reloadContestHandle, reloadContest] = useTriggerUpdate();
  const navigate = useNavigate();

  const logout = useCallback(() => {
    doLogout();
    navigate("/");
  }, [doLogout, navigate]);

  useEffect(() => {
    if (!token) {
      setServerTimeSkew(Loadable.loading());
      setContest(Loadable.loading());
      return;
    }
    client.api
      .get(`/user/${token}`)
      .then((response) => {
        const serverDate = DateTime.fromHTTP(response.headers.date);
        setServerTimeSkew(Loadable.of(DateTime.local().diff(serverDate)));
        setContest(Loadable.of(response.data));
      })
      .catch((response) => {
        logout();
        setServerTimeSkew(Loadable.loading());
        setContest(Loadable.error(response));
      });
  }, [token, logout, reloadContestHandle]);

  const isLoggedIn = useCallback(() => token !== null, [token]);

  return (
    <ContestContext.Provider
      value={{
        data: {
          token,
          serverTimeSkew,
          contest,
        },
        actions: {
          isLoggedIn,
          login,
          logout,
          reloadContest,
        },
      }}
    >
      <CommunicationContextProvider token={token}>
        <SubmissionListContextProvider>
          {children}
        </SubmissionListContextProvider>
      </CommunicationContextProvider>
    </ContestContext.Provider>
  );
}

export function useActions() {
  const context = useContext(ContestContext);
  return useMemo(() => context.actions, [context.actions]);
}

export function useToken() {
  const context = useContext(ContestContext);
  return useMemo(() => context.data.token, [context.data.token]);
}

export function useContest() {
  const context = useContext(ContestContext);
  return useMemo(() => context.data.contest, [context.data.contest]);
}

export function useServerTime() {
  const context = useContext(ContestContext);

  return useMemo(() => () => DateTime.local().minus(context.data.serverTimeSkew.valueOr(Duration.fromMillis(0))), [
    context.data.serverTimeSkew,
  ]);
}
