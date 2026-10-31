const paths: Record<string, string> = {
  pause: 'M8 5v14 M16 5v14',
  home: 'm3 10 9-7 9 7v10H3z M9 20v-7h6v7',
  box: 'm3 7 9-4 9 4v10l-9 4-9-4z M3 7l9 5 9-5 M12 12v9',
  server: 'M4 3h16v7H4z M4 14h16v7H4z M7 6h1 M7 17h1 M16 6h1 M16 17h1',
  user: 'M16 7a4 4 0 1 1-8 0 4 4 0 0 1 8 0 M4 21v-2a8 8 0 0 1 16 0v2z',
  settings:
    'M12 8a4 4 0 1 0 0 8 4 4 0 0 0 0-8 M12 2v3 M12 19v3 M2 12h3 M19 12h3 M5 5l2 2 M17 17l2 2 M5 19l2-2 M17 7l2-2',
  arrow: 'M5 12h14 M13 6l6 6-6 6',
  download: 'M12 3v12 M7 10l5 5 5-5 M4 17v4h16v-4',
  check: 'm5 12 4 4L19 6',
  external: 'M14 3h7v7 M21 3l-11 11 M10 3H3v18h18v-7',
  close: 'm6 6 12 12 M6 18 18 6',
  minus: 'M5 12h14',
  square: 'M5 5h14v14H5z',
  clock: 'M12 3a9 9 0 1 0 0 18 9 9 0 0 0 0-18 M12 7v5l3 2',
  info: 'M12 3a9 9 0 1 0 0 18 9 9 0 0 0 0-18 M12 11v6 M12 7v1',
  search: 'M10 3a7 7 0 1 0 0 14 7 7 0 0 0 0-14 M15 15l6 6',
  shield: 'm12 2 8 4v6c0 5-8 10-8 10S4 17 4 12V6z',
  play: 'm8 4 13 8-13 8z',
};
export function Icon({ name, size = 20 }: { name: string; size?: number }) {
  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.7"
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden="true"
    >
      <path d={paths[name] ?? paths.info} />
    </svg>
  );
}
