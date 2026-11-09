<script setup lang="ts">
import { ref } from 'vue'
import { TournamentList } from '@/components/tournaments'
import { useAuth, useTournaments, type Tournament } from '@/composables'

const { isAuthenticated, user } = useAuth()
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
</script>

<template>
  <main class="min-h-screen bg-secondary/30 px-4 py-12 sm:px-6 lg:px-8">
    <div class="mx-auto max-w-6xl">
      <div class="rounded-3xl bg-linear-to-r from-blue-600 to-violet-600 p-8 text-white shadow-lg">
        <p class="text-sm font-semibold uppercase tracking-wide text-blue-100">Espace joueur</p>
        <h1 class="mt-2 text-3xl font-black sm:text-4xl">
          Bonjour{{ user?.full_name ? ` ${user.full_name}` : '' }} !
        </h1>
        <p class="mt-2 text-blue-100">Voici vos aventures du moment.</p>
        <RouterLink
          v-if="user?.is_superuser"
          to="/tournaments/create"
          class="mt-6 inline-flex items-center rounded-lg bg-white px-5 py-3 text-sm font-bold text-blue-700 shadow-sm transition-colors hover:bg-blue-50 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-white focus-visible:ring-offset-2 focus-visible:ring-offset-blue-600"
        >
          Créer un tournoi
        </RouterLink>
      </div>

      <section class="mt-8" aria-labelledby="my-tournaments-title">
        <h2 id="my-tournaments-title" class="mb-4 text-2xl font-black text-slate-900">
          Mes tournois
        </h2>

        <p v-if="!isAuthenticated" class="rounded-xl border border-dialog-border bg-dialog-bg p-8 text-center text-dialog-muted">
          Connectez-vous pour consulter vos tournois.
        </p>
        <p v-else-if="loadError" role="alert" class="text-danger">{{ loadError }}</p>
        <TournamentList v-else :tournaments="tournaments" />
      </section>
    </div>
  </main>
</template>
