import React, {
  useState, ReactNode, useEffect, useContext, useMemo, useCallback,
} from "react";
import { DateTime, Duration } from "luxon";
import { AxiosResponse, AxiosError } from "axios";
import { client } from "src/TerryClient";
import { notifyError } from "src/utils";
import { Loadable } from "src/Loadable";
import { useTriggerUpdate } from "src/hooks/useTriggerUpdate";
import { useLogin } from "src/hooks/useLogin";
import { StatusData } from "src/types/admin";
import { PackContext } from "./PackContext";

type ContextData = {
  token: string | null;
  serverTimeSkew: Loadable<Duration>;
  status: Loadable<StatusData>;
};

export type StartContestCommand = "reset" | "now" | DateTime;

export type ContextActions = {
  isLoggedIn: () => boolean;
  login: (token: string) => void;
  logout: () => void;
  startContest: (startTime: StartContestCommand) => Promise<void>;
  resetContest: () => Promise<void>;
  setExtraTime: (extraTime: number, userToken?: string) => Promise<void>;
  uploadPack: (file: File) => void;
};

type AdminContextType = {
  data: ContextData;
  actions: ContextActions;
};

export const AdminContext = React.createContext<AdminContextType>({
  data: {
    token: null,
    serverTimeSkew: Loadable.loading(),
    status: Loadable.loading(),
  },
  actions: {
    isLoggedIn: () => false,
    login: () => {},
    logout: () => {},
    startContest: () => Promise.reject(),
    resetContest: () => Promise.reject(),
    setExtraTime: () => Promise.reject(),
    uploadPack: () => {},
  },
});

type AdminContextProps = {
  children: ReactNode;
};

export function AdminContextProvider({ children }: AdminContextProps) {
  const cookieName = "adminToken";

  const [token, login, logout] = useLogin(cookieName);
  const [serverTimeSkew, setServerTimeSkew] = useState<Loadable<Duration>>(Loadable.loading());
  const [status, setStatus] = useState<Loadable<StatusData>>(Loadable.loading());
  const [statusUpdate, triggerStatusUpdate] = useTriggerUpdate();
  const { reloadPack } = useContext(PackContext);

  const startContest = useCallback((startTime: StartContestCommand) => {
    if (!token) throw new Error("You are not logged in");

    const when = typeof startTime === "string" ? startTime : startTime.toUTC().toISO() ?? undefined;
    return client
      .adminApi(token, "/start", { start_time: when })
      .then(() => {
        triggerStatusUpdate();
      })
      .catch((response) => {
        notifyError(response);
        throw response;
      });
  }, [token, triggerStatusUpdate]);
  const resetContest = useCallback(() => {
    if (!token) throw new Error("You are not logged in");
    return client
      .adminApi(token, "/drop_contest")
      .then(() => {
        logout();
        reloadPack();
      })
      .catch((response) => {
        notifyError(response);
      });
  }, [token, logout, reloadPack]);
  const setExtraTime = useCallback((extraTime: number, userToken?: string) => {
    if (!token) throw new Error("You are not logged in");
    const options = {
      extra_time: extraTime.toString(),
      token: userToken,
    };
    if (options.token === undefined) delete options.token;
    return client
      .adminApi(token, "/set_extra_time", options)
      .then(() => {
        triggerStatusUpdate();
      })
      .catch((response) => {
        notifyError(response);
      });
  }, [token, triggerStatusUpdate]);
  const uploadPack = useCallback((file: File) => {
    const data = new FormData();

    data.append("file", file);

    return client.api
      .post("/admin/upload_pack", data)
      .then(() => {
        reloadPack();
      })
      .catch((response) => {
        notifyError(response);
      });
  }, [reloadPack]);

  // handle the login
  useEffect(() => {
    if (!token) {
      setServerTimeSkew(Loadable.loading());
      setStatus(Loadable.loading());
      return;
    }
    client
      .adminApi(token, "/status")
      .then((response: AxiosResponse) => {
        const serverDate = DateTime.fromHTTP(response.headers.date);
        const skew = DateTime.local().diff(serverDate);
        setServerTimeSkew(Loadable.of(skew));
        setStatus(Loadable.of(response.data));
      })
      .catch((response: AxiosError) => {
        notifyError(response);
        logout();
        setServerTimeSkew(Loadable.loading());
        setStatus(Loadable.loading());
      });
  }, [token, statusUpdate, logout]);

  const isLoggedIn = useCallback(() => !status.isLoading(), [status]);
  return (
    <AdminContext.Provider
      value={{
        data: {
          token,
          serverTimeSkew,
          status,
        },
        actions: {
          isLoggedIn,
          login,
          logout,
          startContest,
          resetContest,
          setExtraTime,
          uploadPack,
        },
      }}
    >
      {children}
    </AdminContext.Provider>
  );
}

export function useActions() {
  const context = useContext(AdminContext);
  return useMemo(() => context.actions, [context.actions]);
}

export function useToken() {
  const context = useContext(AdminContext);
  return useMemo(() => context.data.token, [context.data.token]);
}

export function useStatus() {
  const context = useContext(AdminContext);
  return useMemo(() => context.data.status, [context.data.status]);
}

export function useServerTime() {
  const context = useContext(AdminContext);

  return useMemo(() => () => DateTime.local().minus(context.data.serverTimeSkew.valueOr(Duration.fromMillis(0))), [
    context.data.serverTimeSkew,
  ]);
}
