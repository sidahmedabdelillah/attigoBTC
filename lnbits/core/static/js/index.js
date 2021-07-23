new Vue({
  el: '#vue',
  mixins: [windowMixin],
  data: function () {
    return {
      disclaimerDialog: {
        show: false,
        data: {}
      },
      walletName: '',
      email: '',
      password: '',
      terms: false,
    }
  },
  created: async function () {
    const token = localStorage.getItem("token");
    if (token) {
      const requestOptions = {
        method: "GET",
        headers: { "Content-Type": "application/json", "Authorization": `Bearer ${token}` },
      };
      const response = await fetch("/api/v1/get-user", requestOptions);
      const { status, msg, data } = await response.json();
      
      if (status == 200) {
        console.log(msg)
        const { id, walletName } = await data;
        window.location.href = '/wallet?' + (id ? 'usr=' + id + '&' : '') + 'nme=' + walletName;
      } else {
        console.log(msg)
      }
    } else {
    console.log("Token not found in local storage")
    }
  },
  methods: {
    createWallet: function () {
      LNbits.href.createWallet(this.walletName)
    },
    redirectToWallet: function (id, walletName) {
      window.location.href = '/wallet?' + (id ? 'usr=' + id + '&' : '') + 'nme=' + walletName;
    },
    signIn: async function () {
      const requestOptions = {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          email: this.email,
          password: this.password
        })
      };
      const response = await fetch("/api/v1/sign-in", requestOptions);
      const { status, msg, token, id } = await response.json();

      if (status === 200) {
        localStorage.setItem('token', token)
        console.log(msg)
        this.redirectToWallet(id, this.walletName)
        
      };
    },
    signUp: async function () {
      const requestOptions = {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          email: this.email,
          password: this.password,
        })
      };
      const response = await fetch("/api/v1/sign-up", requestOptions);
      const { status, msg } = await response.json();
      if (status == 200) {
        console.log(msg)
        return true
      } else {
        console.log(msg)
        return false
      }
    },
    resetPassword: async function () {
      const requestOptions = {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          email: this.email,
        })
      };
      const response = await fetch("/api/v1/reset-password", requestOptions);
      const { status, msg } = await response.json();

      if (status === 200) {
        console.log(msg)
        
      };
    },
    processing: function () {
      this.$q.notify({
        timeout: 0,
        message: 'Processing...',
        icon: null
      })
    },
    toggleHomeMenu: function (menuChoice) {
      let signUpMenu = document.getElementById("sign-up");
      let signUpForm = document.getElementById("sign-up-form");
      let signInMenu = document.getElementById("sign-in");
      let signInForm = document.getElementById("sign-in-form");
      if (menuChoice == "signUp") {
        signUpForm.style.display = "block";
        signUpMenu.className = "active-tab";
        signInMenu.className = "tab";
        signInMenu.classList.remove("active-tab");
        signInForm.style.display = "none";
      } else if  ((menuChoice == "signIn")) {
        signUpMenu.className = "tab";
        signUpMenu.classList.remove("active-tab");
        signUpForm.style.display = "none";
        signInMenu.className = "active-tab";
        signInForm.style.display = "block";
      }
  },
  }
})
