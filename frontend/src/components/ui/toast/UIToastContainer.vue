<script setup lang="ts">
import { useToast, type ToastItem } from '@/composables/useToast'

const { toasts, remove } = useToast()

function getBgColor(type: ToastItem['type']): string {
  switch (type) {
    case 'success':
      return 'bg-emerald-600 text-white border-emerald-700 shadow-emerald-900/20'
    case 'error':
      return 'bg-red-600 text-white border-red-700 shadow-red-900/20'
    case 'warning':
      return 'bg-amber-600 text-white border-amber-700 shadow-amber-900/20'
    case 'info':
    default:
      return 'bg-blue-600 text-white border-blue-700 shadow-blue-900/20'
  }
}
</script>

<template>
  <aside
    aria-label="Notifications"
    aria-live="polite"
    class="pointer-events-none fixed bottom-5 end-5 z-50 flex max-w-sm flex-col gap-3"
  >
    <TransitionGroup
      enter-active-class="transition duration-200 ease-out"
      enter-from-class="translate-y-3 opacity-0 scale-95"
      enter-to-class="translate-y-0 opacity-100 scale-100"
      leave-active-class="transition duration-150 ease-in"
      leave-from-class="translate-y-0 opacity-100 scale-100"
      leave-to-class="translate-y-2 opacity-0 scale-95"
    >
      <div
        v-for="toast in toasts"
        :key="toast.id"
        role="status"
        :data-type="toast.type"
        :class="[
          'pointer-events-auto flex items-center justify-between gap-3 rounded-xl border px-4 py-3 shadow-lg backdrop-blur-xs',
          getBgColor(toast.type),
        ]"
      >
        <div class="flex items-center gap-2.5">
          <!-- Success check icon -->
          <svg
            v-if="toast.type === 'success'"
            class="size-5 shrink-0"
            xmlns="http://www.w3.org/2000/svg"
            fill="none"
            viewBox="0 0 24 24"
            stroke="currentColor"
            stroke-width="2.5"
            aria-hidden="true"
          >
            <path stroke-linecap="round" stroke-linejoin="round" d="M5 13l4 4L19 7" />
          </svg>
          <!-- Error alert icon -->
          <svg
            v-else-if="toast.type === 'error'"
            class="size-5 shrink-0"
            xmlns="http://www.w3.org/2000/svg"
            fill="none"
            viewBox="0 0 24 24"
            stroke="currentColor"
            stroke-width="2.5"
            aria-hidden="true"
          >
            <circle cx="12" cy="12" r="10" stroke-width="2" />
            <path stroke-linecap="round" d="M12 8v4m0 4h.01" />
          </svg>
          <p class="text-sm font-medium leading-snug">{{ toast.message }}</p>
        </div>
        <button
          type="button"
          aria-label="Fermer la notification"
          class="shrink-0 rounded-md p-1 opacity-80 transition hover:opacity-100 hover:bg-black/15 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-white"
          @click="remove(toast.id)"
        >
          <svg
            class="size-4"
            xmlns="http://www.w3.org/2000/svg"
            fill="none"
            viewBox="0 0 24 24"
            stroke="currentColor"
            stroke-width="2.5"
            aria-hidden="true"
          >
            <path stroke-linecap="round" stroke-linejoin="round" d="M6 18L18 6M6 6l12 12" />
          </svg>
        </button>
      </div>
    </TransitionGroup>
  </aside>
</template>
