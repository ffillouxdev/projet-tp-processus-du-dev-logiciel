import { ref, readonly } from 'vue'

export type ToastType = 'success' | 'error' | 'info' | 'warning'

export interface ToastItem {
  id: number
  message: string
  type: ToastType
  duration: number
}

const toasts = ref<ToastItem[]>([])
let nextId = 1

export function useToast() {
  function remove(id: number) {
    const index = toasts.value.findIndex((t) => t.id === id)
    if (index !== -1) {
      toasts.value.splice(index, 1)
    }
  }

  function add(message: string, type: ToastType = 'info', duration = 4000): number {
    const id = nextId++
    const toast: ToastItem = { id, message, type, duration }
    toasts.value.push(toast)

    if (duration > 0) {
      setTimeout(() => {
        remove(id)
      }, duration)
    }

    return id
  }

  function success(message: string, duration = 4000): number {
    return add(message, 'success', duration)
  }

  function error(message: string, duration = 5000): number {
    return add(message, 'error', duration)
  }

  function clear() {
    toasts.value = []
  }

  return {
    toasts: readonly(toasts),
    add,
    success,
    error,
    remove,
    clear,
  }
}
