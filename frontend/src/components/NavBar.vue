<template>
  <header>
    <nav class="navbar navbar-expand-md navbar-dark bg-dark">
      <div class="container">
        <router-link class="navbar-brand" to="/">🌟Research Analyzer.ai🌟</router-link>
        <button
          class="navbar-toggler"
          type="button"
          data-bs-toggle="collapse"
          data-bs-target="#navbarCollapse"
          aria-controls="navbarCollapse"
          aria-expanded="false"
          aria-label="Toggle navigation"
        >
          <span class="navbar-toggler-icon"></span>
        </button>
        <div class="collapse navbar-collapse" id="navbarCollapse">
          <ul class="navbar-nav me-auto mb-2 mb-md-0">
            <li class="nav-item">
              <router-link class="nav-link" to="/files">My Files</router-link>
            </li>
          </ul>
          <ul class="navbar-nav ms-auto mb-2 mb-md-0">
            <li class="nav-item">
              <router-link class="nav-link" to="/login">Login</router-link>
            </li>
          </ul>
        </div>
      </div>
    </nav>
  </header>
</template>

  
  <script>

  import { defineComponent, computed } from 'vue';
  import { useRouter } from 'vue-router';

  export default defineComponent({
    name: 'NavBar',
    setup() {
      const router = useRouter();

    }
  });


  </script>
  
  <style scoped>
  a {
    cursor: pointer;
  }

  .logo a {
    font-size: 1.3rem;
    font-weight: bold;
    color: white;
    text-decoration: none;
    animation: fade-in 1.5s ease-in-out;
  }
  
  </style>
  