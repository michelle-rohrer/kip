import { SVGProps } from "react";

type IconProps = SVGProps<SVGSVGElement> & { size?: number };

function Base({ size = 20, children, ...props }: IconProps) {
  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth={1.8}
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden="true"
      focusable="false"
      {...props}
    >
      {children}
    </svg>
  );
}

export const IconHome = (p: IconProps) => (
  <Base {...p}>
    <path d="M3.5 10.5 12 4l8.5 6.5" />
    <path d="M5.5 9.8V19a1 1 0 0 0 1 1h11a1 1 0 0 0 1-1V9.8" />
    <path d="M9.5 20v-5.5h5V20" />
  </Base>
);

export const IconSparkle = (p: IconProps) => (
  <Base {...p}>
    <path d="M12 3.5c.6 3.4 2.1 4.9 5.5 5.5-3.4.6-4.9 2.1-5.5 5.5-.6-3.4-2.1-4.9-5.5-5.5 3.4-.6 4.9-2.1 5.5-5.5Z" />
    <path d="M18 15.5c.3 1.6 1 2.3 2.6 2.6-1.6.3-2.3 1-2.6 2.6-.3-1.6-1-2.3-2.6-2.6 1.6-.3 2.3-1 2.6-2.6Z" />
  </Base>
);

export const IconDrop = (p: IconProps) => (
  <Base {...p}>
    <path d="M12 3.5c3.4 3.6 5.5 6.3 5.5 9.1A5.5 5.5 0 0 1 12 18a5.5 5.5 0 0 1-5.5-5.4c0-2.8 2.1-5.5 5.5-9.1Z" />
  </Base>
);

export const IconDumbbell = (p: IconProps) => (
  <Base {...p}>
    <path d="M4 9.5v5M7 7.5v9M17 7.5v9M20 9.5v5M7 12h10" />
  </Base>
);

export const IconPulseAlert = (p: IconProps) => (
  <Base {...p}>
    <path d="M3 12h3.5l2-4.5 3 9 2.5-6 1.7 3.5H21" />
  </Base>
);

export const IconShield = (p: IconProps) => (
  <Base {...p}>
    <path d="M12 3.5 5.5 6v5.4c0 4 2.7 7.4 6.5 8.6 3.8-1.2 6.5-4.6 6.5-8.6V6L12 3.5Z" />
    <path d="M9.5 12.2 11.4 14l3.4-3.6" />
  </Base>
);

export const IconUsers = (p: IconProps) => (
  <Base {...p}>
    <circle cx="9" cy="8.5" r="3.2" />
    <path d="M3.8 19.2c.5-2.9 2.7-4.6 5.2-4.6s4.7 1.7 5.2 4.6" />
    <path d="M16.2 6.2a3 3 0 0 1 0 5.9M17.5 14.9c1.7.5 2.9 1.9 3.2 4.1" />
  </Base>
);

export const IconUser = (p: IconProps) => (
  <Base {...p}>
    <circle cx="12" cy="8.5" r="3.4" />
    <path d="M5.5 19.5c.6-3.2 3.2-5.1 6.5-5.1s5.9 1.9 6.5 5.1" />
  </Base>
);

export const IconSun = (p: IconProps) => (
  <Base {...p}>
    <circle cx="12" cy="12" r="4" />
    <path d="M12 3v2M12 19v2M3 12h2M19 12h2M5.6 5.6l1.4 1.4M17 17l1.4 1.4M18.4 5.6 17 7M7 17l-1.4 1.4" />
  </Base>
);

export const IconMoon = (p: IconProps) => (
  <Base {...p}>
    <path d="M20 14.2A8 8 0 0 1 9.8 4 8.2 8.2 0 1 0 20 14.2Z" />
  </Base>
);

export const IconGlobe = (p: IconProps) => (
  <Base {...p}>
    <circle cx="12" cy="12" r="8.5" />
    <path d="M3.6 9.5h16.8M3.6 14.5h16.8" />
    <path d="M12 3.5c2 2.4 3 5.2 3 8.5s-1 6.1-3 8.5c-2-2.4-3-5.2-3-8.5s1-6.1 3-8.5Z" />
  </Base>
);

export const IconLogout = (p: IconProps) => (
  <Base {...p}>
    <path d="M14 8.2V6.5a1.5 1.5 0 0 0-1.5-1.5h-6A1.5 1.5 0 0 0 5 6.5v11A1.5 1.5 0 0 0 6.5 19h6a1.5 1.5 0 0 0 1.5-1.5v-1.7" />
    <path d="M10.5 12h9M16.8 8.8 20 12l-3.2 3.2" />
  </Base>
);

export const IconChevronRight = (p: IconProps) => (
  <Base {...p}>
    <path d="m9.5 5.5 6.5 6.5-6.5 6.5" />
  </Base>
);

export const IconChevronLeft = (p: IconProps) => (
  <Base {...p}>
    <path d="M14.5 5.5 8 12l6.5 6.5" />
  </Base>
);

export const IconChevronDown = (p: IconProps) => (
  <Base {...p}>
    <path d="m5.5 9 6.5 6.5L18.5 9" />
  </Base>
);

export const IconPlus = (p: IconProps) => (
  <Base {...p}>
    <path d="M12 5.5v13M5.5 12h13" />
  </Base>
);

export const IconCheck = (p: IconProps) => (
  <Base {...p}>
    <path d="m5 12.5 4.5 4.5L19 7.5" />
  </Base>
);

export const IconX = (p: IconProps) => (
  <Base {...p}>
    <path d="M6 6l12 12M18 6 6 18" />
  </Base>
);

export const IconRefresh = (p: IconProps) => (
  <Base {...p}>
    <path d="M19.5 12a7.5 7.5 0 1 1-2.3-5.4" />
    <path d="M19.8 4.5v4.2h-4.2" />
  </Base>
);

export const IconInfo = (p: IconProps) => (
  <Base {...p}>
    <circle cx="12" cy="12" r="8.5" />
    <path d="M12 11v5.2M12 7.8v.2" />
  </Base>
);

export const IconFlame = (p: IconProps) => (
  <Base {...p}>
    <path d="M12 3.2c3.4 3 5 5.6 5 8.4a5 5 0 0 1-10 0c0-1.3.5-2.5 1.4-3.6.5 1 1.2 1.6 2 1.9-.4-2.4.1-4.6 1.6-6.7Z" />
  </Base>
);

export const IconCalendar = (p: IconProps) => (
  <Base {...p}>
    <rect x="4" y="5.5" width="16" height="14" rx="2.5" />
    <path d="M4 10h16M9 3.8v3M15 3.8v3" />
  </Base>
);

export const IconClock = (p: IconProps) => (
  <Base {...p}>
    <circle cx="12" cy="12" r="8.5" />
    <path d="M12 7.5V12l3 1.8" />
  </Base>
);

export const IconTrend = (p: IconProps) => (
  <Base {...p}>
    <path d="M4 15.5 9 10l3.5 3.5L20 6" />
    <path d="M15 6h5v5" />
  </Base>
);

export const IconAlert = (p: IconProps) => (
  <Base {...p}>
    <path d="M12 4.8 3.8 19h16.4L12 4.8Z" />
    <path d="M12 10v4M12 16.8v.2" />
  </Base>
);

export const IconMoonSleep = (p: IconProps) => (
  <Base {...p}>
    <path d="M19.5 14.5A7.6 7.6 0 0 1 9.5 4.6 7.7 7.7 0 1 0 19.5 14.5Z" />
    <path d="M15.5 4.5h4l-4 4h4" />
  </Base>
);

export const IconBattery = (p: IconProps) => (
  <Base {...p}>
    <rect x="3" y="8" width="15" height="8" rx="2.5" />
    <path d="M21 11v2" />
    <path d="M6.5 11v2M10 11v2" />
  </Base>
);

export const IconDownload = (p: IconProps) => (
  <Base {...p}>
    <path d="M12 4.5v10M8.2 11l3.8 3.8L15.8 11" />
    <path d="M5 17.5v1a1.5 1.5 0 0 0 1.5 1.5h11a1.5 1.5 0 0 0 1.5-1.5v-1" />
  </Base>
);

export const IconSettings = (p: IconProps) => (
  <Base {...p}>
    <circle cx="12" cy="12" r="3" />
    <path d="M19.4 13.5a1.6 1.6 0 0 0 .3 1.8l.1.1a2 2 0 1 1-2.8 2.8l-.1-.1a1.6 1.6 0 0 0-1.8-.3 1.6 1.6 0 0 0-1 1.5V20a2 2 0 1 1-4 0v-.2a1.6 1.6 0 0 0-1-1.4 1.6 1.6 0 0 0-1.8.3l-.1.1a2 2 0 1 1-2.8-2.8l.1-.1a1.6 1.6 0 0 0 .3-1.8 1.6 1.6 0 0 0-1.5-1H4a2 2 0 1 1 0-4h.2a1.6 1.6 0 0 0 1.4-1 1.6 1.6 0 0 0-.3-1.8l-.1-.1a2 2 0 0 1 2.8-2.8l.1.1a1.6 1.6 0 0 0 1.8.3H10a1.6 1.6 0 0 0 1-1.5V4a2 2 0 1 1 4 0v.2a1.6 1.6 0 0 0 1 1.5 1.6 1.6 0 0 0 1.8-.3l.1-.1a2 2 0 1 1 2.8 2.8l-.1.1a1.6 1.6 0 0 0-.3 1.8V10a1.6 1.6 0 0 0 1.5 1H20a2 2 0 1 1 0 4h-.2a1.6 1.6 0 0 0-1.4 1Z" />
  </Base>
);

export const IconKey = (p: IconProps) => (
  <Base {...p}>
    <circle cx="8" cy="15" r="4" />
    <path d="M10.9 12.1 20 3" />
    <path d="M17 6l2.5 2.5" />
    <path d="M14.5 8.5 17 11" />
  </Base>
);

export const IconWatch = (p: IconProps) => (
  <Base {...p}>
    <rect x="6.5" y="6.5" width="11" height="11" rx="3" />
    <path d="M9 6.5 9.5 3h5l.5 3.5" />
    <path d="M9 17.5 9.5 21h5l.5-3.5" />
    <path d="M12 9.5V12l1.8 1.1" />
  </Base>
);

export const IconRing = (p: IconProps) => (
  <Base {...p}>
    <ellipse cx="12" cy="13.5" rx="6.5" ry="6" />
    <ellipse cx="12" cy="13.5" rx="3.5" ry="3" />
    <path d="M8 7.5 9 4h6l1 3.5" />
  </Base>
);

export const IconPhone = (p: IconProps) => (
  <Base {...p}>
    <rect x="6.5" y="2.5" width="11" height="19" rx="2.5" />
    <path d="M10.5 5.5h3" />
    <path d="M9.5 13.5h1.6l.9-2 1.4 4 .9-2h1.2" />
  </Base>
);

export const IconLink = (p: IconProps) => (
  <Base {...p}>
    <path d="M10 13.8a3.5 3.5 0 0 0 5.2.4l2.5-2.5a3.5 3.5 0 0 0-5-5l-1.4 1.4" />
    <path d="M14 10.2a3.5 3.5 0 0 0-5.2-.4l-2.5 2.5a3.5 3.5 0 0 0 5 5l1.4-1.4" />
  </Base>
);

export const IconUnlink = (p: IconProps) => (
  <Base {...p}>
    <path d="M9.5 14.5 7.8 16.2a3.5 3.5 0 0 1-5-5l1.7-1.7" />
    <path d="M14.5 9.5l1.7-1.7a3.5 3.5 0 0 1 5 5l-1.7 1.7" />
    <path d="M4 4l16 16" />
  </Base>
);

export const IconCopy = (p: IconProps) => (
  <Base {...p}>
    <rect x="9" y="9" width="11" height="11" rx="2" />
    <path d="M15 9V6a2 2 0 0 0-2-2H6a2 2 0 0 0-2 2v7a2 2 0 0 0 2 2h3" />
  </Base>
);

export const IconHeart = (p: IconProps) => (
  <Base {...p}>
    <path d="M12 20s-7-4.3-7-9a4 4 0 0 1 7-2.6A4 4 0 0 1 19 11c0 4.7-7 9-7 9Z" />
  </Base>
);
