import { faPaperPlane } from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/react-fontawesome";
import { DateTime } from "luxon";
import React, { useState } from "react";
import { Trans, t } from "@lingui/macro";
import { useReloadCommunication } from "src/hooks/useCommunication";
import { client } from "src/TerryClient";
import { notifyError } from "src/utils";
import { Announcement } from "src/components/Announcement";
import { i18n } from "src/i18n";
import { useLogin } from "./CommunicationView";

export function NewAnnouncement() {
  const [token] = useLogin();
  const [title, setTitle] = useState("");
  const [content, setContent] = useState("");
  const [severity, setSeverity] = useState("primary");
  const reload = useReloadCommunication();

  const publish = () => {
    // eslint-disable-next-line no-alert
    if (!window.confirm(i18n._(t`Are you sure?`))) return;
    client.communications?.post("/communications", {
      token, title, content, severity,
    }).then(() => {
      setTitle("");
      setContent("");
      setSeverity("primary");
      reload();
    }).catch((response) => {
      notifyError(response);
    });
  };

  return (
    <>
      <h2><Trans>New announcement</Trans></h2>
      <form onSubmit={(e) => { e.preventDefault(); publish(); }}>
        <div className="form-group">
          <input className="form-control" placeholder={i18n._(t`Title`)} value={title} onChange={(e) => setTitle(e.target.value)} />
        </div>
        <div className="form-group">
          <textarea className="form-control" placeholder={i18n._(t`Content`)} value={content} onChange={(e) => setContent(e.target.value)} />
        </div>
        <div className="form-group">
          <label htmlFor="content"><Trans>Severity</Trans></label>
          <select className="form-control" value={severity} onChange={(e) => setSeverity(e.target.value)}>
            <option value="danger">{i18n._(t`Danger (red)`)}</option>
            <option value="warning">{i18n._(t`Warning (yellow)`)}</option>
            <option value="primary">{i18n._(t`Primary (blue)`)}</option>
            <option value="secondary">{i18n._(t`Secondary (grey)`)}</option>
            <option value="success">{i18n._(t`Success (green)`)}</option>
            <option value="info">{i18n._(t`Info (teal)`)}</option>
            <option value="dark">{i18n._(t`Dark (grey)`)}</option>
          </select>
        </div>
        <hr />
        <h3><Trans>Preview</Trans></h3>
        <Announcement title={title} content={content} severity={severity} date={DateTime.fromJSDate(new Date())} />
        <hr />
        <button type="submit" className="btn btn-primary">
          <FontAwesomeIcon icon={faPaperPlane} />
          {" "}
          <Trans>Publish</Trans>
        </button>
      </form>
    </>
  );
}
