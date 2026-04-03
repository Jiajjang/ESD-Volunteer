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

        async goToVolunteer() {
            const sessionStore = useSessionStore()
            sessionStore.setRole('volunteer')
            await this.$router.push('/')
            this.fetchCurrentUser()
        },

        async goToOrganiser() {
            const sessionStore = useSessionStore()
            sessionStore.setRole('organiser')
            await this.$router.push('/organiser')
            this.fetchCurrentUser()
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
            <div class="dropdown">
                <div class="flex flex-row items-center">
                    <label tabindex="0" class="btn btn-ghost text-xl font-bold normal-case">
                        {{ currentRole }}
                    </label>
                </div>

                <ul
                    tabindex="0"
                    class="dropdown-content menu p-2 shadow bg-base-100 rounded-box w-52 z-50"
                >
                    <li>
                        <button @click="goToVolunteer" class="text-left normal-case">
                            Volunteer Portal
                        </button>
                    </li>
                    <li>
                        <button @click="goToOrganiser" class="text-left normal-case">
                            Organiser Dashboard
                        </button>
                    </li>
                </ul>
            </div>
        </div>

        <div v-if="currentRole === 'Volunteer'" class="navbar-center md:flex gap-8">
            <router-link
                to="/"
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

        <div class="navbar-end flex items-center gap-3">
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
                        class="text-base font-bold flex items-center justify-center h-full px-1"
                        :class="currentRole === 'Organiser' ? 'text-cyan-700' : 'text-emerald-700'"
                    >
                        {{ userInitial }}
                    </span>
                </div>
            </div>
            <span class="font-semibold text-base-content">{{ displayName }}</span>
        </div>
    </div>
</template>
