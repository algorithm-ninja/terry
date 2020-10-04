import { useState, useEffect } from "react";
import { client } from "@terry/shared/_/TerryClient";
import { Loadable } from "@terry/shared/_/Loadable";
import { notifyError } from "@terry/shared/_/utils";
import { Submission } from "@terry/shared/_/types/contest";

export function useSubmission(id: string) {
  const [submission, setSubmission] = useState<Loadable<Submission>>(Loadable.loading());

  useEffect(() => {
    client.api
      .get(`/submission/${id}`)
      .then((response) => {
        setSubmission(Loadable.of(response.data));
      })
      .catch((response) => {
        notifyError(response);
        setSubmission(Loadable.error(response));
      });
  }, [id]);

  return submission;
}
