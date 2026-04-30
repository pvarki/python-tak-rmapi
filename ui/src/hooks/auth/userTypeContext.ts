import { createContext } from "react";

interface UserTypeContextProps {
  userType: "admin" | "user" | null;
  isLoading: boolean;
  error: string | null;
  authType: "mtls" | "jwt" | null;
  otpVerified: boolean;
  setOtpVerified: (verified: boolean) => void;
  redirectTo?: string | null;
  callsign: string | null;
  isValidUser: boolean;
}

const isMock = import.meta.env.VITE_MOCK === "true";

export const UserTypeContext = createContext<UserTypeContextProps>(
  isMock
    ? {
        userType: "user",
        isLoading: false,
        error: null,
        authType: "mtls",
        otpVerified: true,
        setOtpVerified: () => {},
        redirectTo: null,
        callsign: "Fighter01",
        isValidUser: true,
      }
    : {
        userType: null,
        isLoading: true,
        error: null,
        authType: null,
        otpVerified: false,
        setOtpVerified: () => {
          // Placeholder function
        },
        redirectTo: null,
        callsign: null,
        isValidUser: false,
      },
);
