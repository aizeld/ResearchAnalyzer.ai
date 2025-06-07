<template>
    <div class="auth-page">
      <div class="container">
        <div class="row justify-content-center">
          <div class="col-md-6">
            <div class="card shadow-sm p-4">
              <h2 class="text-center mb-4">Register</h2>
              <form @submit.prevent="submitRegister">
                <div class="mb-3">
                  <label for="name" class="form-label">Full Name</label>
                  <input type="text" class="form-control" id="name" v-model="name" required />
                </div>
                <div class="mb-3">
                  <label for="email" class="form-label">Email address</label>
                  <input type="email" class="form-control" id="email" v-model="email" required />
                </div>
                <div class="mb-3">
                  <label for="password" class="form-label">Password</label>
                  <input type="password" class="form-control" id="password" v-model="password" required />
                </div>
                <div class="d-grid">
                  <button type="submit" class="btn btn-primary">Register</button>
                </div>
                <p class="text-center mt-3">
                  Already have an account? <router-link to="/login">Login here</router-link>
                </p>
              </form>
            </div>
          </div>
        </div>
      </div>
    </div>
  </template>
  
  <script>
  export default {
    name: 'RegisterPage',
    data() {
      return {
        name: '',
        email: '',
        password: '',
      };
    },
    methods: {
      submitRegister() {
        // Logic to handle registration
        console.log('Registration submitted', this.name, this.email, this.password);
      },
    },
  };
  </script>
  
  <style scoped>
  .auth-page {
    min-height: 100vh;
    display: flex;
    align-items: center;
    justify-content: center;
    background-color: #f5f8fa;
  }
  
  .card {
    border: none;
    border-radius: 10px;
  }
  
  .btn-primary {
    background-color: #007bff;
    border: none;
  }
  
  .btn-primary:hover {
    background-color: #0056b3;
  }
  </style>
  