export interface NavChild {
  title: string;
  href: string;
}

export interface NavItem {
  title: string;
  href: string;
  /** Icon key - mapped to component in DocsSidebar */
  icon: string;
  children?: NavChild[];
}

export const designSystemNav: NavItem[] = [
  { title: "Overview", href: "/design", icon: "home" },
  { title: "Brand", href: "/design/brand", icon: "book" },
  { title: "Assets", href: "/design/assets", icon: "image" },
  { title: "Colors", href: "/design/colors", icon: "palette" },
  { title: "Typography", href: "/design/typography", icon: "type" },
  { title: "Layout", href: "/design/layout", icon: "layout" },
  {
    title: "Components",
    href: "/design/components",
    icon: "component",
    children: [
      { title: "Alert", href: "/design/components/alert" },
      { title: "Avatar", href: "/design/components/avatar" },
      { title: "Badge", href: "/design/components/badge" },
      { title: "Button", href: "/design/components/button" },
      { title: "Card", href: "/design/components/card" },
      { title: "Chart", href: "/design/components/chart" },
      { title: "Chat", href: "/design/components/chat" },
      { title: "Select", href: "/design/components/select" },
      { title: "Table", href: "/design/components/table" },
    ],
  },
  { title: "Icons", href: "/design/icons", icon: "smile" },
];
