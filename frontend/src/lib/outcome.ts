// What the visitor sees for each enquiry result. Success is shown only for a verified record.
import { isVerifiedSuccess, type EnquiryResponse } from "./contract";
import { fieldErrorsFromServer, type FieldErrors } from "./validation";

export type Outcome =
  | { kind: "success"; title: string; message: string; reference: number | null }
  | { kind: "fix"; title: string; message: string; fields: FieldErrors; other: string[] }
  | { kind: "retry"; title: string; message: string }
  | { kind: "declined"; title: string; message: string }
  | { kind: "failed"; title: string; message: string };

export function outcomeOf(r: EnquiryResponse): Outcome {
  if (isVerifiedSuccess(r)) {
    return {
      kind: "success",
      title: "Your enquiry has been received",
      message:
        r.status === "duplicate"
          ? "We already had this enquiry, so nothing was sent twice. An advisor will contact you."
          : "It is recorded with the sales team. An advisor will contact you using the details you gave.",
      reference: r.crm_id,
    };
  }
  switch (r.status) {
    case "invalid": {
      const { fields, other } = fieldErrorsFromServer(r.errors);
      return { kind: "fix", title: "A few details need fixing", message: "Correct the fields below and send again.", fields, other };
    }
    case "consent_declined":
      return { kind: "declined", title: "Nothing was sent", message: "Without your agreement we do not pass your enquiry to the sales team." };
    case "crm_unavailable":
    case "backend_unavailable":
      return {
        kind: "retry",
        title: "We couldn't confirm your enquiry yet",
        message: "The service did not answer in time. Your answers are kept: try again in a moment. Sending again will not create a duplicate.",
      };
    case "created":
    case "duplicate":
      // A record exists but it did not match what was sent, or was not read back: do not claim success.
      return { kind: "failed", title: "We couldn't verify your enquiry", message: "Please try again later or contact the sales team directly." };
    default:
      return {
        kind: "failed",
        title: "Your enquiry could not be sent",
        message: "This is a problem on our side, not with your answers. Please try again later.",
      };
  }
}
