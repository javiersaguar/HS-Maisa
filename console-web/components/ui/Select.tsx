'use client'

import { Select as BaseSelect } from '@base-ui/react/select'
import { ChevronDown } from 'lucide-react'
import { cn } from '@/lib/utils'

export interface SelectOption<T extends string> {
  value: T
  label: string
}

/**
 * Custom select so the menu can match the trigger radius. Native <select>
 * paints a square OS popup that we cannot style.
 */
export function Select<T extends string>({
  value,
  onChange,
  options,
  'aria-label': ariaLabel,
  className,
  disabled,
  radius = 'lg',
}: {
  value: T
  onChange: (value: T) => void
  options: ReadonlyArray<SelectOption<T>>
  'aria-label'?: string
  className?: string
  disabled?: boolean
  radius?: 'lg' | 'xl'
}) {
  const popupRadius = radius === 'xl' ? 'rounded-xl' : 'rounded-lg'
  const itemRadius = radius === 'xl' ? 'rounded-lg' : 'rounded-md'

  return (
    <BaseSelect.Root
      value={value}
      onValueChange={(next) => {
        if (next == null) return
        onChange(next as T)
      }}
      items={options}
      disabled={disabled}
      modal={false}
    >
      <BaseSelect.Trigger
        aria-label={ariaLabel}
        className={cn(
          'inline-flex w-full min-w-0 items-center justify-between gap-2 border border-[#dfe4de] bg-white px-3 py-2.5 text-left text-[14px] font-medium normal-case tracking-normal text-[#304d43] outline-none transition hover:border-[#b8dcca] focus-visible:border-[#70bda1] focus-visible:ring-4 focus-visible:ring-[#e4f6ee] data-popup-open:border-[#70bda1] data-popup-open:ring-4 data-popup-open:ring-[#e4f6ee] disabled:opacity-60',
          radius === 'xl' ? 'rounded-xl' : 'rounded-lg',
          className,
        )}
      >
        <BaseSelect.Value className="min-w-0 truncate" />
        <BaseSelect.Icon className="flex shrink-0 text-[#789087] transition-transform data-popup-open:rotate-180">
          <ChevronDown className="size-4" />
        </BaseSelect.Icon>
      </BaseSelect.Trigger>
      <BaseSelect.Portal>
        <BaseSelect.Positioner className="z-50 outline-none" sideOffset={6} alignItemWithTrigger={false}>
          <BaseSelect.Popup
            className={cn(
              'w-[var(--anchor-width)] origin-[var(--transform-origin)] overflow-hidden border border-[#dfe7e1] bg-white p-1 shadow-[0_10px_30px_rgba(20,55,45,0.14)] outline-none',
              popupRadius,
            )}
          >
            <BaseSelect.List className="flex flex-col gap-0.5">
              {options.map((option) => (
                <BaseSelect.Item
                  key={option.value}
                  value={option.value}
                  className={cn(
                    'flex min-h-9 cursor-default items-center px-3 text-[14px] text-[#304d43] outline-none select-none data-highlighted:bg-[#eff8f3] data-highlighted:text-[#164f45] data-selected:font-semibold data-selected:text-[#164f45]',
                    itemRadius,
                  )}
                >
                  <BaseSelect.ItemText>{option.label}</BaseSelect.ItemText>
                </BaseSelect.Item>
              ))}
            </BaseSelect.List>
          </BaseSelect.Popup>
        </BaseSelect.Positioner>
      </BaseSelect.Portal>
    </BaseSelect.Root>
  )
}
