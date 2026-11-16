import { describe, it, expect, beforeEach, vi } from 'vitest'
import { useToast } from './useToast'

describe('useToast composable', () => {
  beforeEach(() => {
    vi.useFakeTimers()
    const { clear } = useToast()
    clear()
  })

  it('adds success toast with green/success type', () => {
    const { success, toasts } = useToast()
    const id = success('Score bien enregistré')

    expect(toasts.value.length).toBe(1)
    expect(toasts.value[0]).toEqual({
      id,
      message: 'Score bien enregistré',
      type: 'success',
      duration: 4000,
    })
  })

  it('adds error toast with error type', () => {
    const { error, toasts } = useToast()
    const id = error('Ce tournoi est complet')

    expect(toasts.value.length).toBe(1)
    expect(toasts.value[0]).toEqual({
      id,
      message: 'Ce tournoi est complet',
      type: 'error',
      duration: 5000,
    })
  })

  it('removes toast manually', () => {
    const { success, remove, toasts } = useToast()
    const id = success('Action réussie')
    expect(toasts.value.length).toBe(1)

    remove(id)
    expect(toasts.value.length).toBe(0)
  })

  it('automatically removes toast after duration', () => {
    const { success, toasts } = useToast()
    success('Notification temporaire', 3000)
    expect(toasts.value.length).toBe(1)

    vi.advanceTimersByTime(2999)
    expect(toasts.value.length).toBe(1)

    vi.advanceTimersByTime(2)
    expect(toasts.value.length).toBe(0)
  })

  it('clears all toasts', () => {
    const { success, error, clear, toasts } = useToast()
    success('Message 1')
    error('Message 2')
    expect(toasts.value.length).toBe(2)

    clear()
    expect(toasts.value.length).toBe(0)
  })
})
