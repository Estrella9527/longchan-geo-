# Project Instructions for Claude Code

## UI Framework: shadcn/ui

This project uses **shadcn/ui** as the core component library. All UI development MUST follow these rules.

### Golden Rules

1. **NEVER use raw HTML tags** when a shadcn/ui component exists for that purpose
2. **ALWAYS install components first** via `npx shadcn@latest add <name>` before using them
3. **ALWAYS import from** `@/components/ui/<name>` — never from `@radix-ui` directly
4. **ALWAYS add `"use client"` directive** for interactive components (Dialog, Sheet, Tabs, etc.)
5. **ALWAYS use shadcn CSS variables** for colors (`bg-primary`, `text-muted-foreground`), never hardcoded hex/rgb

### Component Mapping (HTML → shadcn/ui)

When building UI, replace native HTML elements with shadcn/ui components:

| Instead of...           | Use shadcn/ui...                                    |
|------------------------|-----------------------------------------------------|
| `<button>`             | `<Button>` from `@/components/ui/button`            |
| `<input>`              | `<Input>` from `@/components/ui/input`              |
| `<textarea>`           | `<Textarea>` from `@/components/ui/textarea`        |
| `<select>`             | `<Select>` from `@/components/ui/select`            |
| `<input type="checkbox">` | `<Checkbox>` from `@/components/ui/checkbox`     |
| `<input type="radio">` | `<RadioGroup>` from `@/components/ui/radio-group`  |
| `<table>`              | `<Table>` from `@/components/ui/table`              |
| `<dialog>` / modal     | `<Dialog>` from `@/components/ui/dialog`            |
| sidebar drawer         | `<Sheet>` from `@/components/ui/sheet`              |
| tab navigation         | `<Tabs>` from `@/components/ui/tabs`                |
| dropdown               | `<DropdownMenu>` from `@/components/ui/dropdown-menu` |
| tooltip                | `<Tooltip>` from `@/components/ui/tooltip`          |
| card / container       | `<Card>` from `@/components/ui/card`                |
| badge / tag            | `<Badge>` from `@/components/ui/badge`              |
| loading spinner        | `<Skeleton>` from `@/components/ui/skeleton`        |
| progress bar           | `<Progress>` from `@/components/ui/progress`        |
| toggle / switch        | `<Switch>` from `@/components/ui/switch`            |
| date picker            | `<DatePicker>` (Calendar + Popover)                 |
| search / command       | `<Command>` from `@/components/ui/command`          |
| toast / notification   | `<Sonner>` from `@/components/ui/sonner`            |
| breadcrumb             | `<Breadcrumb>` from `@/components/ui/breadcrumb`    |
| pagination             | `<Pagination>` from `@/components/ui/pagination`    |
| form with validation   | `<Form>` + React Hook Form + Zod                    |

### Available shadcn/ui Components (Full List)

Core components that can be installed via `npx shadcn@latest add <name>`:

**Layout & Container**: card, separator, resizable, scroll-area, aspect-ratio, collapsible, sidebar
**Navigation**: breadcrumb, menubar, navigation-menu, pagination, tabs, dropdown-menu, context-menu
**Form Controls**: button, button-group, input, input-group, input-otp, textarea, checkbox, radio-group, select, native-select, switch, slider, toggle, toggle-group, calendar, date-picker, combobox, field, label
**Feedback**: alert, alert-dialog, dialog, drawer, sheet, popover, hover-card, tooltip, sonner, toast, progress, skeleton, spinner, empty
**Data Display**: table, data-table, avatar, badge, card, carousel, chart, kbd, typography
**Utility**: command, direction, item

### Installation Workflow

Before using ANY component in code, ALWAYS run:

```bash
npx shadcn@latest add <component-name>
```

For multiple components at once:

```bash
npx shadcn@latest add button card dialog input label select tabs table badge
```

### Styling Rules

1. Use Tailwind utility classes for layout and spacing
2. Use shadcn CSS variable colors:
   - `bg-background` / `text-foreground` (main)
   - `bg-primary` / `text-primary-foreground` (accent)
   - `bg-secondary` / `text-secondary-foreground`
   - `bg-muted` / `text-muted-foreground` (subtle)
   - `bg-accent` / `text-accent-foreground`
   - `bg-destructive` / `text-destructive-foreground` (danger)
   - `bg-card` / `text-card-foreground`
   - `border-border`, `ring-ring`, `bg-input`
3. Use `cn()` helper from `@/lib/utils` for conditional class merging
4. Responsive design: `sm:`, `md:`, `lg:`, `xl:` prefixes

### Component Composition Patterns

**Card with content:**
```tsx
<Card>
  <CardHeader>
    <CardTitle>Title</CardTitle>
    <CardDescription>Description</CardDescription>
  </CardHeader>
  <CardContent>Content here</CardContent>
  <CardFooter>Footer actions</CardFooter>
</Card>
```

**Form with validation:**
```tsx
<Form {...form}>
  <FormField control={form.control} name="fieldName" render={({ field }) => (
    <FormItem>
      <FormLabel>Label</FormLabel>
      <FormControl><Input {...field} /></FormControl>
      <FormMessage />
    </FormItem>
  )} />
</Form>
```

**Data table:**
```tsx
// Use @tanstack/react-table with shadcn Table components
<Table>
  <TableHeader><TableRow><TableHead>...</TableHead></TableRow></TableHeader>
  <TableBody><TableRow><TableCell>...</TableCell></TableRow></TableBody>
</Table>
```

### File Organization

```
components/
├── ui/              # shadcn/ui base components (auto-generated, do NOT manually edit)
│   ├── button.tsx
│   ├── card.tsx
│   ├── dialog.tsx
│   └── ...
├── [feature]/       # Business components that compose shadcn/ui components
│   ├── data-card.tsx
│   ├── filter-panel.tsx
│   └── ...
lib/
├── utils.ts         # cn() helper (required by shadcn/ui)
hooks/               # Custom hooks
```

### Icons

Use `lucide-react` for icons (shadcn/ui default):

```tsx
import { Search, Settings, ChevronDown } from "lucide-react"
```

### Dark Mode

This project supports dark mode via `next-themes`. Use CSS variables (not hardcoded colors) to ensure automatic theme switching.

### When Updating Existing Pages

When asked to update or improve a page's UI:
1. First check which shadcn/ui components are already installed in `components/ui/`
2. Install any additional needed components
3. Replace custom/raw HTML with shadcn/ui components
4. Ensure all colors use CSS variables
5. Add proper loading states with `<Skeleton>`
6. Add proper empty states with `<Empty>` or custom empty state
7. Ensure responsive design with Tailwind breakpoints
