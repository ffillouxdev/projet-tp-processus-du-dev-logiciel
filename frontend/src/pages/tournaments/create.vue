<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { UIButton, UIInput, UITextArea } from '@/components/ui'
import {
  useToast,
  useTournaments,
  type AssociationSummary,
} from '@/composables'

const router = useRouter()
const { success: toastSuccess, error: toastError } = useToast()
const { createTournament, fetchAssociations } = useTournaments()

const name = ref('')
const description = ref('')
const maxParticipants = ref<number | ''>('')
const startDate = ref('')
const endDate = ref('')
const associationId = ref<number | ''>('')
const associations = ref<AssociationSummary[]>([])
const isSubmitting = ref(false)
const errorMessage = ref('')

onMounted(async () => {
  try {
    const list = await fetchAssociations()
    associations.value = list
    if (list.length > 0 && list[0]) {
      associationId.value = list[0].id
    }
  } catch {
    // If fetching associations fails, default to 1
    associationId.value = 1
  }
})

async function handleSubmit(): Promise<void> {
  if (!name.value.trim()) {
    errorMessage.value = 'Le nom du tournoi est requis.'
    toastError(errorMessage.value)
    return
  }

  if (!associationId.value) {
    errorMessage.value = 'Veuillez sélectionner une association.'
    toastError(errorMessage.value)
    return
  }

  isSubmitting.value = true
  errorMessage.value = ''

  try {
    const tournament = await createTournament({
      name: name.value.trim(),
      description: description.value.trim() || null,
      max_participants: maxParticipants.value ? Number(maxParticipants.value) : null,
      start_date: startDate.value ? new Date(startDate.value).toISOString() : null,
      end_date: endDate.value ? new Date(endDate.value).toISOString() : null,
      association_id: Number(associationId.value),
    })

    toastSuccess('Tournoi créé avec succès !')
    await router.push(`/tournaments/${tournament.id}`)
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
          : 'Impossible de créer le tournoi.'
    errorMessage.value = msg
    toastError(msg)
  } finally {
    isSubmitting.value = false
  }
}
</script>

<template>
  <main class="min-h-screen bg-secondary/30 px-4 py-10 sm:px-6 lg:px-8">
    <div class="mx-auto max-w-2xl">
      <RouterLink to="/" class="text-sm font-semibold text-primary hover:underline">
        Retour aux tournois
      </RouterLink>

      <div class="mt-6 rounded-3xl border border-dialog-border bg-dialog-bg p-8 shadow-sm">
        <h1 class="text-2xl font-black text-slate-900">Créer un nouveau tournoi</h1>
        <p class="mt-2 text-sm text-dialog-muted">
          Remplissez les informations ci-dessous pour configurer votre compétition.
        </p>

        <form class="mt-6 space-y-5" @submit.prevent="handleSubmit">
          <p v-if="errorMessage" role="alert" class="text-sm font-semibold text-danger">
            {{ errorMessage }}
          </p>

          <div>
            <label for="tournament-name" class="block text-sm font-semibold text-slate-800">
              Nom du tournoi *
            </label>
            <UIInput
              id="tournament-name"
              v-model="name"
              type="text"
              required
              class="mt-1"
              placeholder="Ex: Tournoi d'échecs d'automne"
            />
          </div>

          <div>
            <label for="tournament-desc" class="block text-sm font-semibold text-slate-800">
              Description
            </label>
            <UITextArea
              id="tournament-desc"
              v-model="description"
              rows="3"
              class="mt-1"
              placeholder="Règles, détails pratiques, formats..."
            />
          </div>

          <div v-if="associations.length > 1">
            <label for="association-select" class="block text-sm font-semibold text-slate-800">
              Association *
            </label>
            <select
              id="association-select"
              v-model="associationId"
              class="mt-1 block w-full rounded-lg border border-dialog-border bg-dialog-bg p-2.5 text-sm"
              required
            >
              <option
                v-for="assoc in associations"
                :key="assoc.id"
                :value="assoc.id"
              >
                {{ assoc.name }}
              </option>
            </select>
          </div>

          <div class="grid grid-cols-1 gap-4 sm:grid-cols-3">
            <div>
              <label for="max-participants" class="block text-sm font-semibold text-slate-800">
                Max participants
              </label>
              <UIInput
                id="max-participants"
                v-model="maxParticipants"
                type="number"
                min="2"
                class="mt-1"
                placeholder="Ex: 8"
              />
            </div>
            <div>
              <label for="start-date" class="block text-sm font-semibold text-slate-800">
                Date de début
              </label>
              <UIInput
                id="start-date"
                v-model="startDate"
                type="datetime-local"
                class="mt-1"
              />
            </div>
            <div>
              <label for="end-date" class="block text-sm font-semibold text-slate-800">
                Date de fin
              </label>
              <UIInput
                id="end-date"
                v-model="endDate"
                type="datetime-local"
                class="mt-1"
              />
            </div>
          </div>

          <div class="flex justify-end gap-3 pt-4">
            <RouterLink to="/">
              <UIButton variant="ghost" type="button">
                Annuler
              </UIButton>
            </RouterLink>
            <UIButton variant="primary" type="submit" :loading="isSubmitting">
              Créer le tournoi
            </UIButton>
          </div>
        </form>
      </div>
    </div>
  </main>
</template>
