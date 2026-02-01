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
      { title: "Button", href: "/design/components/button" },
      { title: "Badge", href: "/design/components/badge" },
      { title: "Card", href: "/design/components/card" },
      { title: "Table", href: "/design/components/table" },
      { title: "Chart", href: "/design/components/chart" },
      { title: "Alert", href: "/design/components/alert" },
      { title: "Chat", href: "/design/components/chat" },
      { title: "Avatar", href: "/design/components/avatar" },
      { title: "Select", href: "/design/components/select" },
    ],
  },
  { title: "Icons", href: "/design/icons", icon: "smile" },
];
