export type DialogSize = 'sm' | 'md' | 'lg' | 'xl' | 'full'

export interface UIDialogProps {
  title?: string
  description?: string
  canClose?: boolean
  size?: DialogSize
  teleportTo?: string
  closeOnEsc?: boolean
}
