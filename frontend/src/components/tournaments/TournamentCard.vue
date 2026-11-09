<script setup lang="ts">
import { computed } from 'vue'
import type { Tournament } from '@/composables'

const props = defineProps<{
  tournament: Tournament
}>()

const statusContent: Record<
  Tournament['status'],
  { label: string; message: string; card: string; badge: string }
> = {
  draft: {
    label: 'Bientôt disponible',
    message: 'Le tournoi est en préparation.',
    card: 'border-amber-200 bg-amber-50',
    badge: 'bg-amber-200 text-amber-900',
  },
  open: {
    label: 'Inscriptions ouvertes',
    message: 'Le tournoi est prêt, rendez-vous sur la ligne de départ !',
    card: 'border-emerald-200 bg-emerald-50',
    badge: 'bg-emerald-200 text-emerald-900',
  },
  ongoing: {
    label: 'Tournoi en cours',
    message: 'Les matchs sont lancés. Bonne chance !',
    card: 'border-sky-200 bg-sky-50',
    badge: 'bg-sky-200 text-sky-900',
  },
  finished: {
    label: 'Tournoi terminé',
    message: 'Le tournoi est terminé. Bravo pour votre participation !',
    card: 'border-violet-200 bg-violet-50',
    badge: 'bg-violet-200 text-violet-900',
  },
}

const currentStatus = computed(() => statusContent[props.tournament.status])

function formatDate(date: string | null): string | null {
  if (!date) return null

  return new Intl.DateTimeFormat('fr-FR', {
    dateStyle: 'medium',
  }).format(new Date(date))
}
</script>

<template>
  <RouterLink
    :to="`/tournaments/${tournament.id}`"
    :class="[
      'block rounded-2xl border p-5 shadow-sm transition-transform hover:-translate-y-1 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary',
      currentStatus.card,
    ]"
  >
    <article>
      <div class="flex items-start justify-between gap-4">
        <div class="flex items-center gap-3">
          <h3 class="text-xl font-bold text-slate-900">{{ tournament.name }}</h3>
        </div>
        <span :class="['rounded-full px-3 py-1 text-center text-xs font-bold', currentStatus.badge]">
          {{ currentStatus.label }}
        </span>
      </div>

      <p class="mt-4 text-sm font-medium text-slate-700">
        {{ currentStatus.message }}
      </p>

      <p v-if="tournament.description" class="mt-2 text-sm text-slate-600">
        {{ tournament.description }}
      </p>

      <dl class="mt-5 flex flex-wrap gap-x-6 gap-y-2 text-sm text-slate-600">
        <div v-if="formatDate(tournament.start_date)">
          <dt class="font-bold">Début</dt>
          <dd>{{ formatDate(tournament.start_date) }}</dd>
        </div>
        <div v-if="formatDate(tournament.end_date)">
          <dt class="font-bold">Fin</dt>
          <dd>{{ formatDate(tournament.end_date) }}</dd>
        </div>
      </dl>
    </article>
  </RouterLink>
</template>
