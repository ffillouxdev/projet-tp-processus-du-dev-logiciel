<script setup lang="ts">
import { RegisterForm } from '@/components/auth'
import { UITitle, UIText } from '@/components/ui'
</script>

<template>
  <main class="min-h-screen flex flex-col justify-center py-12 sm:px-6 lg:px-8 bg-secondary/30">
    <div class="max-w-6xl mx-auto">
      <UITitle tag="h1" class="!mb-0">
        Créer un compte
      </UITitle>
      <!-- Registration Card -->
      <div class="mt-8 sm:mx-auto sm:w-full sm:max-w-md px-4 sm:px-0">
        <div class="bg-dialog-bg py-8 px-6 shadow-md sm:rounded-2xl sm:px-10 border border-dialog-border">
          <RegisterForm />
          <!-- Link to Login -->
          <div class="mt-6 pt-6 border-t border-dialog-border text-center">
            <UIText type="subtext">
              Vous avez déjà un compte ?
              <RouterLink to="/login"
                class="font-medium text-primary hover:text-primary-hover hover:underline ms-1 transition-colors">
                Se connecter
              </RouterLink>
            </UIText>
          </div>
        </div>
      </div>
    </div>
  </main>
</template>
