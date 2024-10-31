// context/AuthContext.js
import React, { createContext, useState, useContext, useEffect } from 'react';
import axios from 'axios';
import * as SecureStore from 'expo-secure-store';

const AuthContext = createContext({});

const TOKEN_KEY = "my_key";
export const API_URL = "http://10.0.0.169:3000"

export const AuthProvider = ({ children }) => {
  const [authState, setAuthState] = useState({token: null, authorised: null});
  const [loading, setLoading] = useState(true);

  // const login = () => setAuthState(true);
  // const logout = () => setAuthState(false);
  
  useEffect(() => {
    
    const loadToken = async ()=> {
      
      const accessToken = await SecureStore.getItemAsync(TOKEN_KEY);

        if (accessToken) {
          axios.defaults.headers.common['Authorization'] = `Bearer ${accessToken}`;
          
          setAuthState({
            token: accessToken,
            authorised: true
          });
        }
        setLoading(false);
    }
    loadToken();
    
  })
  


  const register = async (username, password) => {
    try {
      return await axios.post(`${API_URL}/register`, {username, password})
    } catch (error) {
      
      return { error: true, msg: (error).response.data.err}
    }
  }

  const login = async (username, password) => {
    try {
      
      const result = await axios.post(`${API_URL}/login`, {username, password})

      // console.log(result);

      await SecureStore.setItemAsync(TOKEN_KEY, result.data.accessToken);

      setAuthState({
        token: result.data.accessToken,
        authorised: true
      });

      print(authState.token)

      

      axios.defaults.headers.common['Authorization'] = `Bearer ${result.data.accessToken}`;


      return result;
      
    } catch (error) {
      return { error: true, msg: (error).response.data.err}
    }
  }

  const logout = async () => {
    try {
      await SecureStore.deleteItemAsync(TOKEN_KEY);

      axios.defaults.headers.common['Authorization'] = '';

      setAuthState({
        token: null,
        authorised: false
      });
      
    } catch (error) {
      return { error: true, msg: error}
    }
  }


  return (
    <AuthContext.Provider value={{ onRegister: register, onLogin: login, onLogout: logout, authState, loading, setLoading}}>
      {children}
    </AuthContext.Provider>
  );
};


export const useAuth = () => useContext(AuthContext);