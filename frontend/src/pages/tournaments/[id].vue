<script setup lang="ts">
import { computed, onMounted, onUnmounted, ref } from 'vue'
import { useRoute } from 'vue-router'
import { TournamentBracket } from '@/components/tournaments'
import { UIButton, UIDialog } from '@/components/ui'
import {
  useAuth,
  useToast,
  useTournaments,
  type TournamentStatus,
  type TournamentParticipant,
  type TournamentBracketMatch,
  type UserMembership,
} from '@/composables'

const route = useRoute('/tournaments/[id]')
const { user, fetchMyMemberships } = useAuth()
const { success: toastSuccess, error: toastError } = useToast()
const {
  fetchTournament,
  fetchTournamentBracket,
  joinTournament,
  leaveTournament,
  startTournament,
  reportScore,
  declareForfeit,
  connectTournamentWebSocket,
} = useTournaments()
const tournamentId = Number(route.params.id)
const [tournamentResponse, bracketResponse] = await Promise.all([
  fetchTournament(tournamentId),
  fetchTournamentBracket(tournamentId),
])
const tournament = ref(tournamentResponse)
const bracket = ref(bracketResponse)
const userMemberships = ref<UserMembership[]>([])
const isJoining = ref(false)
const isLeaving = ref(false)
const isStarting = ref(false)
const isStartDialogOpen = ref(false)
const isScoreDialogOpen = ref(false)
const isForfeitDialogOpen = ref(false)
const selectedMatch = ref<TournamentBracketMatch | null>(null)
const scorePlayer1 = ref<number | ''>('')
const scorePlayer2 = ref<number | ''>('')
const forfeitUserId = ref<number | null>(null)
const isReportingScore = ref(false)
const isForfeiting = ref(false)
const registrationError = ref('')
const startError = ref('')
const scoreError = ref('')
const forfeitError = ref('')
const isRegistered = computed(() =>
  tournament.value.participants.some((participant) => participant.user_id === user.value?.id),
)

const isOrganizer = computed(() => {
  if (!user.value) return false
  if (user.value.is_superuser) return true
  const assocId = tournament.value.association_id ?? tournament.value.association?.id
  return userMemberships.value.some(
    (m) =>
      m.association_id === assocId &&
      ['admin', 'organizer'].includes(m.role?.name?.toLowerCase() ?? ''),
  )
})

let socket: WebSocket | null = null

onMounted(async () => {
  if (user.value) {
    try {
      userMemberships.value = await fetchMyMemberships()
    } catch {
      userMemberships.value = []
    }
  }

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
    toastSuccess('Inscription confirmée ! Vous participez à ce tournoi.')
  } catch (error) {
    const msg =
      typeof error === 'object' &&
      error !== null &&
      'data' in error &&
      typeof error.data === 'object' &&
      error.data !== null &&
      'detail' in error.data &&
      typeof error.data.detail === 'string'
        ? error.data.detail === 'Tournament is full'
          ? 'Ce tournoi est complet.'
          : error.data.detail
        : error instanceof Error
          ? error.message
          : 'Impossible de rejoindre ce tournoi.'
    registrationError.value = msg
    toastError(msg)
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
    toastSuccess('Vous avez quitté le tournoi avec succès.')
  } catch (error) {
    const msg = error instanceof Error ? error.message : 'Impossible de quitter ce tournoi.'
    registrationError.value = msg
    toastError(msg)
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
    toastSuccess('Tournoi lancé avec succès ! L’arbre a été généré.')
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
    toastError(startError.value)
  } finally {
    isStarting.value = false
  }
}

function canInteractWithMatch(match: TournamentBracketMatch): boolean {
  if (!user.value) return false
  if (tournament.value.status !== 'ongoing') return false
  if (match.winner_id !== null || match.status !== 'pending') {
    return false
  }

  const [p1, p2] = match.players
  if (!p1.id || !p2.id) return false
  if (
    p1.name === 'En attente' ||
    p2.name === 'En attente' ||
    p1.name === 'BYE' ||
    p2.name === 'BYE'
  ) {
    return false
  }

  const isMatchParticipant = user.value.id === p1.id || user.value.id === p2.id
  return isMatchParticipant || isOrganizer.value
}

function handleSelectMatch(match: TournamentBracketMatch): void {
  // Prevent any unauthorized interaction
  if (!canInteractWithMatch(match)) return

  selectedMatch.value = match
  scorePlayer1.value = match.players[0].score ?? 0
  scorePlayer2.value = match.players[1].score ?? 0
  scoreError.value = ''
  isScoreDialogOpen.value = true
}

async function handleReportScore(): Promise<void> {
  if (!selectedMatch.value) return
  if (!canInteractWithMatch(selectedMatch.value)) return
  if (scorePlayer1.value === '' || scorePlayer2.value === '') {
    scoreError.value = 'Veuillez saisir un score pour chaque joueur.'
    toastError(scoreError.value)
    return
  }

  isReportingScore.value = true
  scoreError.value = ''

  try {
    await reportScore(
      tournamentId,
      selectedMatch.value.id,
      Number(scorePlayer1.value),
      Number(scorePlayer2.value),
    )
    toastSuccess('Score bien enregistré')
    isScoreDialogOpen.value = false
    bracket.value = await fetchTournamentBracket(tournamentId)
  } catch (error) {
    const msg =
      typeof error === 'object' &&
      error !== null &&
      'data' in error &&
      typeof error.data === 'object' &&
      error.data !== null &&
      'detail' in error.data &&
      typeof error.data.detail === 'string'
        ? error.data.detail
        : error instanceof Error
          ? error.message
          : 'Impossible d’enregistrer le score.'
    scoreError.value = msg
    toastError(msg)
  } finally {
    isReportingScore.value = false
  }
}

const canDeclareForfeit = computed(() => {
  if (!selectedMatch.value) return false
  return canInteractWithMatch(selectedMatch.value)
})

const hasInteractiveMatches = computed(() =>
  bracket.value.some((m) => canInteractWithMatch(m)),
)

function handleOpenForfeitDialog(): void {
  if (!selectedMatch.value) return
  const [p1, p2] = selectedMatch.value.players
  if (user.value?.id === p1.id) {
    forfeitUserId.value = p1.id
  } else if (user.value?.id === p2.id) {
    forfeitUserId.value = p2.id
  } else {
    forfeitUserId.value = p1.id
  }
  forfeitError.value = ''
  isForfeitDialogOpen.value = true
}

async function handleConfirmForfeit(): Promise<void> {
  if (!selectedMatch.value || !forfeitUserId.value) return
  isForfeiting.value = true
  forfeitError.value = ''

  try {
    const res = await declareForfeit(
      tournamentId,
      selectedMatch.value.id,
      forfeitUserId.value,
    )
    toastSuccess(res.message || 'Forfait enregistré. L’adversaire est qualifié pour le tour suivant.')
    isForfeitDialogOpen.value = false
    isScoreDialogOpen.value = false
    bracket.value = await fetchTournamentBracket(tournamentId)
  } catch (error) {
    const msg =
      typeof error === 'object' &&
      error !== null &&
      'data' in error &&
      typeof error.data === 'object' &&
      error.data !== null &&
      'detail' in error.data &&
      typeof error.data.detail === 'string'
        ? error.data.detail
        : error instanceof Error
          ? error.message
          : 'Impossible de déclarer le forfait.'
    forfeitError.value = msg
    toastError(msg)
  } finally {
    isForfeiting.value = false
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
        <div v-if="isOrganizer && ['draft', 'open'].includes(tournament.status)" class="mt-6">
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

      <UIDialog
        v-model="isScoreDialogOpen"
        title="Saisir le score du match"
        description="Renseignez le score final des deux adversaires."
      >
        <div v-if="selectedMatch" class="space-y-4">
          <div class="flex items-center justify-between gap-4 rounded-xl border border-dialog-border bg-secondary/10 p-3">
            <span class="font-bold text-gray-900 dark:text-gray-100">{{ selectedMatch.players[0].name }}</span>
            <input
              v-model.number="scorePlayer1"
              type="number"
              min="0"
              class="w-20 rounded-lg border border-dialog-border bg-dialog-bg p-2 text-center text-lg font-bold"
              placeholder="0"
            />
          </div>
          <div class="flex items-center justify-between gap-4 rounded-xl border border-dialog-border bg-secondary/10 p-3">
            <span class="font-bold text-gray-900 dark:text-gray-100">{{ selectedMatch.players[1].name }}</span>
            <input
              v-model.number="scorePlayer2"
              type="number"
              min="0"
              class="w-20 rounded-lg border border-dialog-border bg-dialog-bg p-2 text-center text-lg font-bold"
              placeholder="0"
            />
          </div>
          <p v-if="scoreError" role="alert" class="text-sm font-semibold text-danger">
            {{ scoreError }}
          </p>
        </div>
        <template #footer="{ close }">
          <div class="flex w-full items-center justify-between gap-3">
            <UIButton
              v-if="canDeclareForfeit"
              variant="danger"
              type="button"
              :disabled="isReportingScore || isForfeiting"
              @click="handleOpenForfeitDialog"
            >
              Déclarer forfait
            </UIButton>
            <div class="ms-auto flex items-center gap-2">
              <UIButton variant="ghost" :disabled="isReportingScore" @click="close">
                Annuler
              </UIButton>
              <UIButton variant="primary" :loading="isReportingScore" @click="handleReportScore">
                Enregistrer le score
              </UIButton>
            </div>
          </div>
        </template>
      </UIDialog>

      <UIDialog
        v-model="isForfeitDialogOpen"
        title="Déclarer forfait"
        description="Cette action est irréversible. L'adversaire sera automatiquement déclaré vainqueur (3-0) et qualifié pour le tour suivant."
      >
        <div v-if="selectedMatch" class="space-y-4">
          <div v-if="isOrganizer" class="space-y-3">
            <label class="block text-sm font-semibold text-slate-800 dark:text-gray-200">
              Sélectionnez le participant déclarant forfait (ou absent) :
            </label>
            <div class="space-y-2">
              <label
                v-for="player in selectedMatch.players"
                :key="player.id ?? player.name"
                class="flex cursor-pointer items-center gap-3 rounded-lg border border-dialog-border bg-secondary/10 p-3 hover:bg-secondary/20"
              >
                <input
                  v-model="forfeitUserId"
                  type="radio"
                  name="forfeit-player-choice"
                  :value="player.id"
                  class="text-primary focus:ring-primary"
                />
                <span class="font-bold text-gray-900 dark:text-gray-100">{{ player.name }}</span>
              </label>
            </div>
          </div>
          <p v-else class="text-sm text-slate-700 dark:text-gray-300">
            Voulez-vous vraiment déclarer forfait pour ce match ? Votre adversaire remportera la victoire technique (3-0) et sera propulsé au tour suivant.
          </p>
          <p v-if="forfeitError" role="alert" class="text-sm font-semibold text-danger">
            {{ forfeitError }}
          </p>
        </div>
        <template #footer="{ close }">
          <UIButton variant="ghost" :disabled="isForfeiting" @click="close">
            Annuler
          </UIButton>
          <UIButton variant="danger" :loading="isForfeiting" @click="handleConfirmForfeit">
            Confirmer le forfait
          </UIButton>
        </template>
      </UIDialog>

      <div class="mt-8 grid gap-8 lg:grid-cols-[minmax(0,1fr)_18rem]">
        <section class="rounded-2xl border border-dialog-border bg-dialog-bg p-6 shadow-sm" aria-labelledby="bracket-title">
          <h2 id="bracket-title" class="mb-5 text-2xl font-black text-slate-900">Bracket</h2>
          <TournamentBracket
            :matches="bracket"
            :is-match-interactive="canInteractWithMatch"
            @select-match="handleSelectMatch"
          />
          <p v-if="hasInteractiveMatches" class="mt-3 text-xs font-semibold text-primary">
            Cliquez sur votre match en cours pour saisir les scores ou déclarer forfait.
          </p>
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
