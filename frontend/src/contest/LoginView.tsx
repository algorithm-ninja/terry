import React, { createRef, useState } from "react";
import { Trans, t } from "@lingui/macro";
import { i18n } from "../i18n";
import { useActions, useContest } from "./ContestContext";

export default function LoginView() {
  const tokenRef = createRef<HTMLInputElement>();
  const { login } = useActions();
  const contest = useContest();
  const [isLoading, setIsLoading] = useState(false);

  const doLogin = () => {
    if (!tokenRef.current) return;
    setIsLoading(true);
    login(tokenRef.current.value);
  };

  return (
    <div className="jumbotron">
      <h1 className={"text-center"}>
        <Trans>Please login</Trans>
      </h1>
      <form
        action=""
        onSubmit={(e) => {
          e.preventDefault();
          doLogin();
        }}
      >
        <div className="form-group">
          <label htmlFor="token" className="sr-only">
            <Trans>Token</Trans>
          </label>
          <input
            autoComplete="off"
            name="token"
            id="token"
            ref={tokenRef}
            className="form-control text-center"
            required
            placeholder={i18n._(t`Token`)}
            type="text"
          />
        </div>
        <input type="submit" className="btn btn-primary" value={i18n._(t`Login`)} />
        {contest.isError() ? (
          <div className="alert alert-danger mt-2" role="alert">
            <strong>
              <Trans>Error</Trans>
            </strong>{" "}
            {contest.error().response?.data.message}
          </div>
        ) : isLoading ? (
          <Trans>Loading...</Trans>
        ) : null}
      </form>
    </div>
  );
}
