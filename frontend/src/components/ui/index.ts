/**
 * Core UI Component Library
 *
 * This module exports all reusable UI components for the CIRA application.
 * Components follow the design system defined in specs/07-ui-components.md.
 */

// Button
export { Button } from './Button';
export type { ButtonProps } from './Button';

// Input
export { Input } from './Input';
export type { InputProps } from './Input';

// Select
export { Select } from './Select';
export type { SelectProps, SelectOption } from './Select';

// Checkbox
export { Checkbox } from './Checkbox';
export type { CheckboxProps } from './Checkbox';

// Table
export { Table } from './Table';
export type { TableProps, TableColumn } from './Table';

// Card
export { Card } from './Card';
export type { CardProps } from './Card';

// Modal
export { Modal } from './Modal';
export type { ModalProps } from './Modal';

// Toast
export { ToastProvider, useToast } from './Toast';
export type { Toast, ToastType, ToastContextValue } from './Toast';

// ProgressBar
export { ProgressBar } from './ProgressBar';
export type { ProgressBarProps } from './ProgressBar';

// Badge
export { Badge } from './Badge';
export type { BadgeProps, BadgeVariant } from './Badge';
export { getStatusBadgeVariant } from './badgeUtils';

// Tabs
export { Tabs } from './Tabs';
export type { TabsProps, Tab } from './Tabs';

// Skeleton
export { Skeleton, SkeletonText, SkeletonCard, SkeletonTable } from './Skeleton';
export type { SkeletonProps } from './Skeleton';

// Slider
export { Slider } from './Slider';
export type { SliderProps } from './Slider';
