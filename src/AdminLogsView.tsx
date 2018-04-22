import * as React from 'react';
import { Object } from 'core-js';
import { Link } from 'react-router-dom';
import { FontAwesomeIcon } from '@fortawesome/react-fontawesome'
import { faTimes } from '@fortawesome/fontawesome-free-solid'
import ModalView from './ModalView';
import "./AdminLogsView.css";
import PromiseView from './PromiseView';
import { AbsoluteDateView } from './datetime.views';
import { DateTime } from 'luxon';
import { AdminSession } from './admin.models';
import ObservablePromise from './ObservablePromise';
import { InjectedTranslateProps, InjectedI18nProps } from 'react-i18next';


const LOG_LEVELS: any = {
  DEBUG: {
    color: 'secondary',
  },
  INFO: {
    color: 'info',
  },
  WARNING: {
    color: 'warning',
  },
  ERROR: {
    color: 'danger',
  },
}

type LogItem = {
  level: string
  category: string
  message: string
  date: string
}

type Props = {
  session: AdminSession
} & InjectedTranslateProps & InjectedI18nProps

type State = {
  level: string
  category: string
  filter: string
}

export default class AdminLogsView extends React.Component<Props, State> {
  logsPromise: any;
  refreshLogsPromise?: ObservablePromise;
  interval?: NodeJS.Timer;

  constructor(props: Props) {
    super(props);
    this.state = {
      level: "INFO",
      category: "",
      filter: "",
    };
  }

  componentWillMount() {
    this.loadLogs();
  }

  componentDidMount() {
    this.interval = setInterval(() => this.refreshLogs(), 5000);
  }

  componentWillUnmount() {
    if (this.interval) {
      clearInterval(this.interval);
      delete this.interval;
    }
  }

  loadLogs() {
    this.refreshLogsPromise = undefined;
    this.logsPromise = this.doLoadLogs();
    this.forceUpdate();
  }

  doLoadLogs() {
    const options: any = {
      start_date: "2000-01-01T00:00:00.000",
      end_date: "2030-01-01T00:00:00.000",
      level: this.state.level
    };
    if (this.state.category) {
      options.category = this.state.category;
    }
    return this.props.session.loadLogs(options);
  }

  refreshLogs() {
    const promise = this.refreshLogsPromise = this.doLoadLogs();
    this.refreshLogsPromise.delegate.then(() => {
      if (this.refreshLogsPromise !== promise) return;
      this.logsPromise = promise;
      this.forceUpdate();
    })
  }

  componentDidUpdate(_props: Props, state: State) {
    if (state.level !== this.state.level || state.category !== this.state.category)
      this.loadLogs();
  }

  changeLevel(level: string) {
    this.setState({ level });
  }

  changeCategory(category: string) {
    this.setState({ category });
  }

  changeFilter(filter: string) {
    this.setState({ filter });
  }

  filter(log: LogItem) {
    const filter = this.state.filter.toLowerCase();
    if (!filter) return true;
    return log.message.toLowerCase().indexOf(filter) !== -1;
  }

  render() {
    const { t } = this.props;

    return (
      <ModalView contentLabel={t("logs.title")} returnUrl={"/admin"}>
        <div className="modal-header">
          <h5 className="modal-title">
            {t("logs.title")}
          </h5>
          <Link to={"/admin"} role="button" className="close" aria-label="Close">
            <span aria-hidden="true">&times;</span>
          </Link>
        </div>
        <div className="modal-body no-padding">
          <div className="form-group p-2 mb-0">
            <div className="btn-group mb-1" role="group" aria-label="Choose log level">
              {Object.entries(LOG_LEVELS).map(([level, obj]) => (
                <button
                  key={level}
                  className={[
                    'btn',
                    ((this.state.level === level) ? 'active' : ''),
                    'btn-' + obj.color
                  ].join(' ')}
                  onClick={() => this.changeLevel(level)}
                >
                  {t("logs.levels." + level)}
                </button>
              ))}
            </div>
            <input
              placeholder={t("logs.category filter")} className="form-control mb-1" value={this.state.category}
              onChange={(e) => this.changeCategory(e.target.value)}
            />
            <input placeholder={t("logs.message filter")} className="form-control" value={this.state.filter}
              onChange={(e) => this.changeFilter(e.target.value)} />
          </div>
          <div className="terry-log-table no-padding">
            <table className="table">
              <thead>
                <tr>
                  <th>{t("logs.date")}</th>
                  <th>{t("logs.category")}</th>
                  <th>{t("logs.level")}</th>
                  <th>{t("logs.message")}</th>
                </tr>
              </thead>
              <tbody>
                <PromiseView promise={this.logsPromise}
                  renderFulfilled={(logs: { items: LogItem[] }) => {
                    const items = logs.items.filter((l) => this.filter(l));
                    if (items.length === 0) return <tr><td colSpan={4}>{t("no messages yet")}</td></tr>;
                    return items.map((log, i) =>
                      <tr key={i} className={"table-" + LOG_LEVELS[log.level].color}>
                        <td>
                          <AbsoluteDateView {...this.props} clock={() => this.props.session.serverTime()} date={DateTime.fromISO(log.date)} />
                        </td>
                        <td>
                          <button className="btn btn-link" onClick={() => { this.changeCategory(log.category) }}>
                            {log.category}
                          </button>
                        </td>
                        <td>
                          <button className="btn btn-link" onClick={() => { this.changeLevel(log.level) }}>
                            {t("logs.levels." + log.level)}
                          </button>
                        </td>
                        <td><pre>{log.message}</pre></td>
                      </tr>
                    );
                  }}
                  renderPending={() => <tr><td colSpan={4}>{t("loading")}</td></tr>}
                  renderRejected={() => <tr><td colSpan={4}>{t("error")}</td></tr>}
                />
              </tbody>
            </table>
          </div>
        </div>
        <div className="modal-footer">
          <Link to={"/admin"} role="button" className="btn btn-primary">
            <FontAwesomeIcon icon={faTimes} /> {t("close")}
          </Link>
        </div>
      </ModalView>
    );
  }
}
