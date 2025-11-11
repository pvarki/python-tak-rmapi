// utils/detectOS.ts
export enum OS {
  Android = "android",
  iOS = "ios",
  Windows = "windows",
  Tracker = "tracker",
}

export const detectOS = (): OS => {
  if (typeof window === "undefined") return OS.Android;

  const ua =
    window.navigator.userAgent ||
    window.navigator.vendor ||
    (window as any).opera;

  if (/android/i.test(ua)) return OS.Android;
  if (/iPad|iPhone|iPod/.test(ua)) return OS.iOS;
  if (/Windows NT/.test(ua)) return OS.Windows;

  //Return most likely platform
  return OS.Android;
};
