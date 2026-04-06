<script>
import { useVolunteerStore } from '@/stores/volunteer'
import { useOrganiserStore } from '@/stores/organiser'
import { useSessionStore } from '@/stores/currentRole'

export default {
    name: 'navBar',

    data() {
        return {
            user: null,
            loading: false,
            error: null,
        }
    },

    computed: {
        sessionStore() {
            return useSessionStore()
        },

        currentRole() {
            return this.sessionStore.currentRole === 'organiser' ? 'Organiser' : 'Volunteer'
        },

        isOrganiserView() {
            return this.sessionStore.currentRole === 'organiser'
        },

        currentId() {
            if (this.isOrganiserView) {
                return useOrganiserStore().organiserId
            }
            return useVolunteerStore().volunteerId
        },

        displayName() {
            if (this.isOrganiserView) {
                return this.user?.organiser_name?.trim() || 'Organiser'
            }
            return this.user?.volunteer_name?.trim() || 'Volunteer'
        },

        userInitial() {
            return this.displayName.charAt(0).toUpperCase()
        },
    },

    methods: {
        async fetchCurrentUser() {
            this.loading = true
            this.error = null

            try {
                const endpoint = this.isOrganiserView
                    ? `http://localhost:5004/organiser/${this.currentId}`
                    : `http://localhost:5002/volunteer/${this.currentId}`

                const response = await fetch(endpoint)
                if (!response.ok) throw new Error('API failed')

                const data = await response.json()
                this.user = data.data
            } catch (err) {
                console.error('API Error:', err)
                this.error = err.message
                this.user = null
            } finally {
                this.loading = false
            }
        },
    },

    mounted() {
        this.fetchCurrentUser()
    },

    watch: {
        'sessionStore.currentRole'() {
            this.fetchCurrentUser()
        },
    },
}
</script>

<template>
    <div class="navbar bg-base-100 border-b border-base-300 px-6">
        <div class="navbar-start">
            <div class="flex flex-row items-center">
                <h3 class="text-2xl font-bold">
                    {{ currentRole }}
                </h3>
            </div>
        </div>

        <div v-if="currentRole === 'Volunteer'" class="navbar-center md:flex gap-8">
            <router-link
                to="/volunteer"
                class="font-semibold text-base-content/80 hover:text-emerald-600 hover:underline decoration-2 underline-offset-4 transition-all duration-300 px-2 py-1 rounded-md"
            >
                Home
            </router-link>

            <router-link
                to="/events"
                class="font-semibold text-base-content/80 hover:text-emerald-600 hover:underline decoration-2 underline-offset-4 transition-all duration-300 px-2 py-1 rounded-md"
            >
                Events
            </router-link>
        </div>
        <div class="navbar-end">
            <div class="dropdown dropdown-end">
                <div
                    tabindex="0"
                    role="button"
                    class="btn btn-ghost h-auto min-h-0 px-2 normal-case hover:bg-base-200"
                >
                    <div class="flex items-center gap-3">
                        <div class="avatar online placeholder">
                            <div
                                class="w-8 rounded-full ring ring-offset-2"
                                :class="
                                    currentRole === 'Organiser'
                                        ? 'bg-cyan-100 ring-cyan-200'
                                        : 'bg-emerald-100 ring-emerald-200'
                                "
                            >
                                <span
                                    class="flex h-full items-center justify-center px-1 text-base font-bold"
                                    :class="
                                        currentRole === 'Organiser'
                                            ? 'text-cyan-700'
                                            : 'text-emerald-700'
                                    "
                                >
                                    {{ userInitial }}
                                </span>
                            </div>
                        </div>

                        <span class="font-semibold text-base-content">{{ displayName }}</span>

                        <svg
                            xmlns="http://www.w3.org/2000/svg"
                            class="h-4 w-4 text-base-content/60"
                            fill="none"
                            viewBox="0 0 24 24"
                            stroke="currentColor"
                            stroke-width="2"
                        >
                            <path
                                stroke-linecap="round"
                                stroke-linejoin="round"
                                d="M19 9l-7 7-7-7"
                            />
                        </svg>
                    </div>
                </div>

                <ul
                    tabindex="0"
                    class="menu menu-sm dropdown-content z-1 mt-3 w-44 rounded-box border border-base-200 bg-base-100 p-2 shadow"
                >   
                    <li>
                        <RouterLink to="/" class="text-error"> Logout </RouterLink>
                    </li>
                </ul>
            </div>
        </div>
    </div>
</template>
