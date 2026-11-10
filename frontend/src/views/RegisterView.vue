<script setup>
import { ref } from 'vue'
const loginName=ref(''),password=ref(''),confirmPassword=ref(''),busy=ref(false),error=ref(''),created=ref(false)
async function register(){
  if(busy.value)return
  error.value=''
  if(password.value!==confirmPassword.value){error.value='两次输入的密码不一致';return}
  busy.value=true
  try{
    const response=await fetch('/api/auth/register',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({login_name:loginName.value,password:password.value})})
    const result=await response.json().catch(()=>({}))
    if(!response.ok)throw new Error(result.error||'注册失败，请稍后重试')
    created.value=true;password.value='';confirmPassword.value=''
  }catch(reason){error.value=reason.message||'网络连接失败，请稍后重试'}
  finally{busy.value=false}
}
</script>
<template>
  <div class="workspace registration-page">
    <main class="registration-card">
      <RouterLink class="registration-back" to="/login">← 返回登录</RouterLink>
      <span class="registration-caption">PERSONALRAG · 个人资料库</span>
      <h1>{{created?'账号已创建':'创建你的账号'}}</h1>
      <p class="page-description">{{created?'注册成功，请使用新账号登录。':'拥有独立的资料库，整理原文、版本与知识。'}}</p>
      <RouterLink v-if="created" class="registration-login" to="/login">前往登录</RouterLink>
      <form v-else @submit.prevent="register" :aria-busy="busy">
        <div><label for="register-name">用户名</label><input id="register-name" v-model="loginName" autocomplete="username" minlength="3" maxlength="32" pattern="[a-zA-Z0-9_][a-zA-Z0-9_-]{2,31}" required :disabled="busy" aria-describedby="register-name-help"/><small id="register-name-help">3–32 位字母、数字、下划线或短横线，不区分大小写</small></div>
        <div><label for="register-password">密码</label><input id="register-password" v-model="password" type="password" autocomplete="new-password" minlength="10" maxlength="128" required :disabled="busy"/><small>10–128 位，请使用独立的长密码</small></div>
        <div><label for="register-confirm">确认密码</label><input id="register-confirm" v-model="confirmPassword" type="password" autocomplete="new-password" minlength="10" maxlength="128" required :disabled="busy"/></div>
        <p v-if="error" class="error" role="alert">{{error}}</p>
        <button type="submit" class="primary" :disabled="busy">{{busy?'正在创建账号…':'注册账号'}}</button>
      </form>
    </main>
  </div>
</template>
