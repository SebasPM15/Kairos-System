'use client'

import type { ReactNode } from 'react'
import { Toast } from '@base-ui/react/toast'
import { X } from 'lucide-react'

// Lets code outside React components (the dashboard context) raise toasts too
const manager = Toast.createToastManager()

const SUCCESS_MS = 4000
const ERROR_MS = 8000

// Short-lived feedback only: a toast confirms something already done and never holds the only way to fix a problem
export const toast = {
  success: (title: string, description?: string) =>
    manager.add({ type: 'success', title, description, timeout: SUCCESS_MS }),
  // Not priority 'high': Base UI hides those from assistive tech (aria-hidden) until focused, so the error
  // would go unannounced. role="alert" on the toast (see ToastList) makes it assertive instead.
  error: (title: string, description?: string) =>
    manager.add({ type: 'error', title, description, timeout: ERROR_MS }),
}

function ToastList() {
  const { toasts } = Toast.useToastManager()
  return <Toast.Portal>
    <Toast.Viewport className="toast-viewport" aria-label="Notificaciones">
      {toasts.map((item) => <Toast.Root key={item.id} toast={item} className="toast" data-type={item.type} role={item.type === 'error' ? 'alert' : undefined}>
        <Toast.Content className="toast-content">
          <div className="toast-text">
            <Toast.Title className="toast-title" />
            <Toast.Description className="toast-description" />
          </div>
          <Toast.Close className="toast-close" aria-label="Cerrar aviso"><X aria-hidden="true" /></Toast.Close>
        </Toast.Content>
      </Toast.Root>)}
    </Toast.Viewport>
  </Toast.Portal>
}

export function Toaster({ children }: { children?: ReactNode }) {
  return <Toast.Provider toastManager={manager} limit={3}>
    {children}
    <ToastList />
  </Toast.Provider>
}
