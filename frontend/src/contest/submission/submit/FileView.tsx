import React from "react";
import { filesize } from "filesize";
import { DateTime } from "luxon";
import "./FileView.css";
import { Trans } from "@lingui/macro";
import { RelativeDate } from "src/components/RelativeDate";

type Props = {
  file: File;
};

export function FileView({ file }: Props) {
  return (
    <table className="terry-file-view">
      <tbody>
        <tr>
          <th>
            <Trans>File:</Trans>
          </th>
          <td>{file.name}</td>
        </tr>
        {file.lastModified && (
          <tr>
            <th>
              <Trans>Last update:</Trans>
            </th>
            <td>
              <RelativeDate clock={() => DateTime.local()} date={DateTime.fromMillis(file.lastModified)} />
            </td>
          </tr>
        )}
        <tr>
          <th>
            <Trans>Size:</Trans>
          </th>
          <td>{filesize(file.size) as string}</td>
        </tr>
      </tbody>
    </table>
  );
}
