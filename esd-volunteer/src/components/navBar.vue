<script>
export default {
  name: 'navBar'
  
}
</script>

<template>
    <div class="navbar bg-base-100 border-b border-base-300 px-6">
        <div class="navbar-start">
            <a class="btn btn-ghost text-xl font-bold normal-case">
                Volunteer
            </a>
        </div>

        <div class="navbar-center hidden md:flex gap-8">
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
                <div class="w-8 rounded-full bg-emerald-100 ring ring-emerald-200 ring-offset-2">
                    <span class="text-base font-bold text-emerald-700 flex items-center justify-center h-full px-1">
                        S
                    </span>
                </div>
            </div>
            <span class="font-semibold text-base-content">Siti Ng</span>
        </div>
    </div>
</template>
