<script setup lang="ts">
import TournamentCard from './TournamentCard.vue'
import type { Tournament } from '@/composables'

defineProps<{
  tournaments: Tournament[]
}>()
</script>

<template>
  <div v-if="tournaments.length" class="grid gap-4 md:grid-cols-2">
    <TournamentCard
      v-for="tournament in tournaments"
      :key="tournament.id"
      :tournament="tournament"
    />
  </div>
  <p
    v-else
    class="rounded-2xl border-2 border-dashed border-blue-200 bg-blue-50 p-8 text-center font-medium text-blue-800"
  >
    Aucun tournoi pour le moment. Revenez bientôt !
  </p>
</template>
