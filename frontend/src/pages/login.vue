<script setup lang="ts">
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { LoginForm, type LoginFormData } from '@/components/auth'
import { useAuth } from '@/composables'
import { UITitle, UIText } from '@/components/ui'

const router = useRouter()
const { login } = useAuth()
const loginError = ref('')

async function handleLogin(data: LoginFormData): Promise<void> {
  loginError.value = ''

  try {
    await login(data)
    await router.push('/')
  } catch (error) {
    loginError.value =
      error instanceof Error ? error.message : 'Une erreur est survenue lors de la connexion.'
  }
}
</script>

<template>
  <main class="min-h-screen flex flex-col justify-center py-12 sm:px-6 lg:px-8 bg-secondary/30">
    <div class="max-w-6xl mx-auto">
      <UITitle tag="h1" class="!mb-0"> Se connecter </UITitle>
      <!-- Login Card -->
      <div class="mt-8 sm:mx-auto sm:w-full sm:max-w-md px-4 sm:px-0">
        <div
          class="bg-dialog-bg py-8 px-6 shadow-md sm:rounded-2xl sm:px-10 border border-dialog-border"
        >
          <p v-if="loginError" role="alert" class="mb-4 text-sm text-danger">
            {{ loginError }}
          </p>
          <LoginForm @submit="handleLogin" />
          <!-- Link to Register -->
          <div class="mt-6 pt-6 border-t border-dialog-border text-center">
            <UIText type="subtext">
              Vous n’avez pas encore de compte ?
              <RouterLink
                to="/register"
                class="font-medium text-primary hover:text-primary-hover hover:underline ms-1 transition-colors"
              >
                Créer un compte
              </RouterLink>
            </UIText>
          </div>
        </div>
      </div>
    </div>
  </main>
</template>
