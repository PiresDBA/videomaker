export const fmtDuration = (s) => {
  if (!s || s < 0) return "-";
  const m = Math.floor(s / 60);
  const sec = Math.round(s % 60);
  return m ? `${m}m ${sec}s` : `${sec}s`;
};
