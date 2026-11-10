<script setup lang="ts">
import { computed, onMounted, onUnmounted, ref } from 'vue'
import { useRoute } from 'vue-router'
import { TournamentBracket } from '@/components/tournaments'
import { UIButton, UIDialog } from '@/components/ui'
import {
  useAuth,
  useTournaments,
  type TournamentStatus,
  type TournamentParticipant,
} from '@/composables'

const route = useRoute('/tournaments/[id]')
const { user } = useAuth()
const {
  fetchTournament,
  fetchTournamentBracket,
  joinTournament,
  leaveTournament,
  startTournament,
  connectTournamentWebSocket,
} = useTournaments()
const tournamentId = Number(route.params.id)
const [tournamentResponse, bracketResponse] = await Promise.all([
  fetchTournament(tournamentId),
  fetchTournamentBracket(tournamentId),
])
const tournament = ref(tournamentResponse)
const bracket = ref(bracketResponse)
const isJoining = ref(false)
const isLeaving = ref(false)
const isStarting = ref(false)
const isStartDialogOpen = ref(false)
const registrationError = ref('')
const startError = ref('')
const isRegistered = computed(() =>
  tournament.value.participants.some((participant) => participant.user_id === user.value?.id),
)

let socket: WebSocket | null = null

onMounted(() => {
  socket = connectTournamentWebSocket(tournamentId, (data) => {
    if (data.bracket) {
      bracket.value = data.bracket
    }
    if (data.status) {
      tournament.value.status = data.status
    }
    if (typeof data.winner_id !== 'undefined') {
      tournament.value.winner_id = data.winner_id
    }
  })
})

onUnmounted(() => {
  if (socket) {
    socket.close()
    socket = null
  }
})

async function handleJoin(): Promise<void> {
  isJoining.value = true
  registrationError.value = ''

  try {
    const participant: TournamentParticipant = await joinTournament(tournamentId)
    tournament.value.participants.push(participant)
  } catch (error) {
    registrationError.value =
      error instanceof Error ? error.message : 'Impossible de rejoindre ce tournoi.'
  } finally {
    isJoining.value = false
  }
}

async function handleLeave(): Promise<void> {
  isLeaving.value = true
  registrationError.value = ''

  try {
    await leaveTournament(tournamentId)
    tournament.value.participants = tournament.value.participants.filter(
      (participant) => participant.user_id !== user.value?.id,
    )
  } catch (error) {
    registrationError.value =
      error instanceof Error ? error.message : 'Impossible de quitter ce tournoi.'
  } finally {
    isLeaving.value = false
  }
}

async function handleStart(): Promise<void> {
  isStarting.value = true
  startError.value = ''

  try {
    const response = await startTournament(tournamentId)
    tournament.value.status = response.status
    bracket.value = response.bracket
    isStartDialogOpen.value = false
  } catch (error) {
    if (
      typeof error === 'object' &&
      error !== null &&
      'data' in error &&
      typeof error.data === 'object' &&
      error.data !== null &&
      'detail' in error.data &&
      error.data.detail === 'Tournament must have at least 2 participants to be started'
    ) {
      startError.value = 'Le tournoi doit avoir au moins deux inscrits pour être lancé.'
    } else {
      startError.value =
        error instanceof Error ? error.message : 'Impossible de lancer ce tournoi.'
    }
  } finally {
    isStarting.value = false
  }
}

const statusContent: Record<TournamentStatus, { label: string; color: string }> = {
  draft: { label: 'Bientôt disponible', color: 'bg-amber-100 text-amber-800' },
  open: { label: 'Inscriptions ouvertes', color: 'bg-emerald-100 text-emerald-800' },
  ongoing: { label: 'Tournoi en cours', color: 'bg-sky-100 text-sky-800' },
  finished: { label: 'Tournoi terminé', color: 'bg-violet-100 text-violet-800' },
}

function formatDate(date: string | null): string | null {
  if (!date) return null

  return new Intl.DateTimeFormat('fr-FR', { dateStyle: 'medium' }).format(new Date(date))
}
</script>

<template>
  <main class="min-h-screen bg-secondary/30 px-4 py-10 sm:px-6 lg:px-8">
    <div class="mx-auto max-w-6xl">
      <RouterLink to="/" class="text-sm font-semibold text-primary hover:underline">
        Retour aux tournois
      </RouterLink>

      <header class="mt-6 rounded-3xl bg-linear-to-r from-blue-600 to-violet-600 p-8 text-white shadow-lg">
        <div class="flex flex-wrap items-start justify-between gap-4">
          <div>
            <p class="text-sm font-semibold uppercase tracking-wide text-blue-100">
              {{ tournament.association.name }}
            </p>
            <h1 class="mt-2 text-3xl font-black sm:text-4xl">{{ tournament.name }}</h1>
          </div>
          <span :class="['rounded-full px-4 py-2 text-sm font-bold', statusContent[tournament.status].color]">
            {{ statusContent[tournament.status].label }}
          </span>
        </div>
        <p v-if="tournament.description" class="mt-5 max-w-2xl text-blue-50">
          {{ tournament.description }}
        </p>
        <div v-if="tournament.status === 'open'" class="mt-6">
          <div v-if="!isRegistered" class="flex flex-wrap gap-3">
            <UIButton variant="secondary" :loading="isJoining" @click="handleJoin">
              Rejoindre le tournoi
            </UIButton>
          </div>
          <div v-else class="flex flex-wrap items-center gap-3">
            <p class="text-sm font-semibold text-blue-100">Vous participez à ce tournoi.</p>
            <UIButton variant="danger" :loading="isLeaving" @click="handleLeave">
              Quitter le tournoi
            </UIButton>
          </div>
          <p v-if="registrationError" role="alert" class="mt-3 text-sm font-semibold text-red-100">
            {{ registrationError }}
          </p>
        </div>
        <div v-if="user?.is_superuser && ['draft', 'open'].includes(tournament.status)" class="mt-6">
          <UIButton variant="primary" @click="isStartDialogOpen = true">
            Lancer le tournoi
          </UIButton>
        </div>
      </header>

      <UIDialog
        v-model="isStartDialogOpen"
        title="Lancer le tournoi"
        description="Cette action va démarrer le tournoi et générer son bracket."
      >
        <p>Voulez-vous vraiment lancer « {{ tournament.name }} » ?</p>
        <p v-if="startError" role="alert" class="mt-4 text-sm font-semibold text-danger">
          {{ startError }}
        </p>
        <template #footer="{ close }">
          <UIButton variant="ghost" :disabled="isStarting" @click="close">
            Annuler
          </UIButton>
          <UIButton variant="primary" :loading="isStarting" @click="handleStart">
            Confirmer le lancement
          </UIButton>
        </template>
      </UIDialog>

      <div class="mt-8 grid gap-8 lg:grid-cols-[minmax(0,1fr)_18rem]">
        <section class="rounded-2xl border border-dialog-border bg-dialog-bg p-6 shadow-sm" aria-labelledby="bracket-title">
          <h2 id="bracket-title" class="mb-5 text-2xl font-black text-slate-900">Bracket</h2>
          <TournamentBracket :matches="bracket" />
        </section>

        <aside class="space-y-6">
          <section class="rounded-2xl border border-dialog-border bg-dialog-bg p-6 shadow-sm">
            <h2 class="text-lg font-black text-slate-900">Informations</h2>
            <dl class="mt-4 space-y-3 text-sm text-slate-600">
              <div v-if="formatDate(tournament.start_date)">
                <dt class="font-bold">Début</dt>
                <dd>{{ formatDate(tournament.start_date) }}</dd>
              </div>
              <div v-if="formatDate(tournament.end_date)">
                <dt class="font-bold">Fin</dt>
                <dd>{{ formatDate(tournament.end_date) }}</dd>
              </div>
              <div>
                <dt class="font-bold">Participants</dt>
                <dd>{{ tournament.total_participants ?? tournament.participants.length }}</dd>
              </div>
            </dl>
          </section>

          <section class="rounded-2xl border border-dialog-border bg-dialog-bg p-6 shadow-sm">
            <h2 class="text-lg font-black text-slate-900">Participants</h2>
            <ul class="mt-4 space-y-2 text-sm text-slate-600">
              <li v-for="participant in tournament.participants" :key="participant.user_id">
                {{ participant.user.full_name || participant.user.username }}
              </li>
              <li v-if="!tournament.participants.length" class="text-dialog-muted">
                Aucun participant pour le moment.
              </li>
            </ul>
          </section>
        </aside>
      </div>
    </div>
  </main>
</template>
