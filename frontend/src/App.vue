<template>
  <Suspense>
    <template #default>
      <RouterView />
    </template>
    <template #fallback>
      <main class="flex min-h-screen items-center justify-center bg-secondary/30">
        <p class="text-dialog-muted">Chargement…</p>
      </main>
    </template>
  </Suspense>
</template>
