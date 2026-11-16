<script setup lang="ts">
import { ref } from 'vue'
import { TournamentList } from '@/components/tournaments'
import { UIButton } from '@/components/ui'
import { useAuth, useToast, useTournaments, type Tournament } from '@/composables'

const { isAuthenticated, user, logout } = useAuth()
const { success: toastSuccess } = useToast()
const { fetchVisibleTournaments } = useTournaments()
const tournaments = ref<Tournament[]>([])
const loadError = ref('')

if (isAuthenticated.value) {
  try {
    tournaments.value = await fetchVisibleTournaments()
  } catch (error) {
    loadError.value =
      error instanceof Error ? error.message : 'Impossible de charger vos tournois.'
  }
}

async function handleLogout(): Promise<void> {
  await logout()
  tournaments.value = []
  toastSuccess('Vous avez été déconnecté avec succès.')
}
</script>

<template>
  <main class="min-h-screen bg-secondary/30 px-4 py-8 sm:px-6 lg:px-8">
    <div class="mx-auto max-w-6xl">
      <!-- Top Navigation Bar -->
      <nav class="mb-6 flex items-center justify-between border-b border-dialog-border/40 pb-4">
        <RouterLink to="/" class="text-xl font-black tracking-tight text-slate-900">
          🏆 Tournois
        </RouterLink>
        <div class="flex items-center gap-3">
          <template v-if="isAuthenticated">
            <span class="hidden text-sm font-medium text-slate-600 sm:inline">
              {{ user?.full_name || user?.username }}
            </span>
            <UIButton variant="ghost" class="text-xs sm:text-sm" @click="handleLogout">
              Se déconnecter
            </UIButton>
          </template>
          <template v-else>
            <RouterLink
              to="/login"
              class="inline-flex items-center rounded-lg bg-primary px-4 py-2 text-sm font-semibold text-white shadow-sm transition-colors hover:bg-primary-hover focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary focus-visible:ring-offset-2"
            >
              Se connecter
            </RouterLink>
            <RouterLink
              to="/register"
              class="inline-flex items-center rounded-lg border border-dialog-border bg-dialog-bg px-4 py-2 text-sm font-semibold text-slate-700 shadow-sm transition-colors hover:bg-secondary/20 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary focus-visible:ring-offset-2"
            >
              Créer un compte
            </RouterLink>
          </template>
        </div>
      </nav>

      <!-- Hero Banner -->
      <div class="rounded-3xl bg-linear-to-r from-blue-600 to-violet-600 p-8 text-white shadow-lg">
        <p class="text-sm font-semibold uppercase tracking-wide text-blue-100">Espace joueur</p>
        <h1 class="mt-2 text-3xl font-black sm:text-4xl">
          {{ isAuthenticated ? `Bonjour${user?.full_name ? ` ${user.full_name}` : ''} !` : 'Bienvenue sur la plateforme !' }}
        </h1>
        <p class="mt-2 text-blue-100">
          {{ isAuthenticated ? 'Voici vos aventures du moment.' : 'Connectez-vous pour rejoindre des tournois et suivre vos matchs en direct.' }}
        </p>

        <div class="mt-6 flex flex-wrap gap-3">
          <RouterLink
            v-if="user?.is_superuser"
            to="/tournaments/create"
            class="inline-flex items-center rounded-lg bg-white px-5 py-3 text-sm font-bold text-blue-700 shadow-sm transition-colors hover:bg-blue-50 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-white focus-visible:ring-offset-2 focus-visible:ring-offset-blue-600"
          >
            Créer un tournoi
          </RouterLink>
          <template v-if="!isAuthenticated">
            <RouterLink
              to="/login"
              class="inline-flex items-center rounded-lg bg-white px-5 py-3 text-sm font-bold text-blue-700 shadow-sm transition-colors hover:bg-blue-50 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-white focus-visible:ring-offset-2 focus-visible:ring-offset-blue-600"
            >
              Se connecter
            </RouterLink>
            <RouterLink
              to="/register"
              class="inline-flex items-center rounded-lg border border-white/40 bg-white/10 px-5 py-3 text-sm font-bold text-white backdrop-blur-sm transition-colors hover:bg-white/20 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-white focus-visible:ring-offset-2 focus-visible:ring-offset-blue-600"
            >
              Créer un compte
            </RouterLink>
          </template>
        </div>
      </div>

      <!-- Tournaments Section -->
      <section class="mt-8" aria-labelledby="my-tournaments-title">
        <h2 id="my-tournaments-title" class="mb-4 text-2xl font-black text-slate-900">
          Mes tournois
        </h2>

        <div
          v-if="!isAuthenticated"
          class="rounded-xl border border-dialog-border bg-dialog-bg p-8 text-center"
        >
          <p class="text-sm font-medium text-dialog-muted">
            Connectez-vous pour consulter vos tournois et vos inscriptions.
          </p>
          <div class="mt-4 flex justify-center gap-3">
            <RouterLink
              to="/login"
              class="inline-flex items-center rounded-lg bg-primary px-4 py-2 text-sm font-bold text-white shadow-sm transition-colors hover:bg-primary-hover"
            >
              Se connecter
            </RouterLink>
            <RouterLink
              to="/register"
              class="inline-flex items-center rounded-lg border border-dialog-border bg-dialog-bg px-4 py-2 text-sm font-bold text-slate-700 shadow-sm transition-colors hover:bg-secondary/20"
            >
              Créer un compte
            </RouterLink>
          </div>
        </div>
        <p v-else-if="loadError" role="alert" class="text-danger">{{ loadError }}</p>
        <TournamentList v-else :tournaments="tournaments" />
      </section>
    </div>
  </main>
</template>
