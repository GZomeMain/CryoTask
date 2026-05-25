---
name: UI/UX Modernization
description: Workflow for upgrading the CustomTkinter interface to a premium, Windows 11-style aesthetic with rich animations and responsive layouts.
---

# 🎨 UI/UX Modernization Skill

This skill focuses on transforming the technical interface into a premium user experience that "WOWs" the user while maintaining clarity and performance.

## 💎 Design Principles
- **Vibrant Minimalism**: Use clean lines but rich, curated colors (not generic primary colors).
- **Interactive Feedback**: Every action should have a visual response (hover states, status dots, subtle transitions).
- **Glassmorphism & Depth**: Utilize layers and subtle borders to create a sense of hierarchy.
- **Modern Typography**: Ensure font sizes and weights create a clear information architecture.

## 🛠️ Implementation Guide

### 1. Color Palette & Tokens
Define a central theme dictionary instead of hardcoding colors:
- `PRIMARY`: Deep Azure or Vibrant Purple.
- `SUCCESS`: Emerald Green (for "Resumed" state).
- `WARNING`: Amber Gold (for "Trimmed" state).
- `DANGER`: Ruby Red (for "Suspended" state).
- `CARD_BG`: Slightly elevated dark grey with low opacity for glass effect.

### 2. Component Enhancements
- **The "Card" View**: Upgrade process cards with rounded corners (12px-16px), subtle inner borders, and shadow simulations.
- **Status Dots**: Implement pulsate animations or glow effects for active/inactive status.
- **RAM Bar**: Use a gradient progress bar (e.g., Green -> Yellow -> Red) instead of a solid color.
- **Icons**: Ensure all icons are high-resolution SVG/PNGs that scale well.

### 3. Layout Perfection
- **Dynamic Scaling**: Use grid weighting correctly so the app looks good at 400x600 and 1200x800.
- **Empty States**: Design beautiful "No results found" or "No pinned apps" views using `generate_image` for illustration assets.
- **Transitions**: If possible within `ctk`, implement smooth fading or sliding when switching between presets and the main list.

### 4. Accessibility
- High contrast options.
- keyboard navigation (`Tab` flow).
- Clear tooltips for complex technical actions (like "Trim working set").

## 🚀 Proactive Steps
1.  **Mockup Generation**: Use `generate_image` to create a visual target for the new UI.
2.  **Asset Refresh**: Check `assets/` and replace dated graphics with modern equivalents.
3.  **Theme Switcher**: Ensure the app respects Windows System Theme (Dark/Light) or provides a sleek toggle.

---
*Created by Antigravity - Optimized for CryoTask Upgrade.*
