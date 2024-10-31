// navigation/AuthNavigator.js
import React, {useState} from 'react';
import {  View, Text , Button, Alert, StyleSheet, TextInput, TouchableOpacity } from "react-native";
import { createNativeStackNavigator } from '@react-navigation/native-stack';
import { useAuth } from './AuthContext';
import * as SecureStore from "expo-secure-store";




const LoginScreen = ({ navigation }) => {
  const { onLogin, loading } = useAuth();

  const [isLoading, setLoading] = useState(false);
  const [userName, setUserName] = useState('');
  const [password, setPassword] = useState('');



  if (loading) {
    return <SplashScreen text="loading"></SplashScreen>
  }

  const login = async () => {
    
    const result = await onLogin(userName, password);
    if (result && result.error) {
      Alert.alert(result.msg);
      setLoading(false);
    } else {
      setLoading(false);
    }
  }

  if (isLoading) {
    return <SplashScreen text="logging you in"></SplashScreen>
  }

  return (
    <View style={styles.container}>
      <TextInput autoCapitalize="none" style={styles.inputText} placeholder="Username" onChangeText={(text) => setUserName(text)}></TextInput>
      <TextInput autoCapitalize="none" style={styles.inputText} placeholder="Password" secureTextEntry={true} onChangeText={(text) => setPassword(text)}></TextInput>
      <TouchableOpacity style = {styles.belowInputButton} disabled={isLoading} title="Login" onPress={login} >
        <Text style={styles.loginText}>Login</Text>
      </TouchableOpacity>
      <TouchableOpacity style = {styles.subButton} disabled={isLoading} title="Register" onPress={() => navigation.navigate('Register')}>
        <Text style={styles.registerText}>Register</Text>
      </TouchableOpacity>
    </View>
  );
};


const RegisterScreen = ({ navigation }) => {

  const { onRegister } = useAuth();

  const [isLoading, setLoading] = useState(false);
  const [userName, setUserName] = useState('');
  const [password, setPassword] = useState('');

  const register = async () => {
    setLoading(true)
    const result = await onRegister(userName, password);
    if (result && result.error) {
      Alert.alert(result.msg);
      setLoading(false);
    } else {
      navigation.navigate('Login');
      setLoading(false);
    }
  }

  return (
    <View style={styles.container}>
      
      <TextInput autoCapitalize="none" style={styles.inputText} placeholder="Username" onChangeText={(text) => setUserName(text)}></TextInput>
      <TextInput autoCapitalize="none" style={styles.inputText} placeholder="Password" secureTextEntry={true} onChangeText={(text) => setPassword(text)}></TextInput>
      <TouchableOpacity disabled={isLoading} style = {styles.belowInputButton} title="Register" onPress={register}>
        <Text style={styles.loginText}>Register</Text>
      </TouchableOpacity>
        
      {/* <Button title="Back" onPress={() => navigation.navigate('Login')} /> */}
    </View>
  );
};

const SplashScreen = ({text}) => {

  return (
    <View style={styles.container}>
      <Text style={styles.loginText}>{text}</Text>
    </View>
  );
};


const Stack = createNativeStackNavigator();

const AuthNavigator = () => (
  <Stack.Navigator>
    <Stack.Screen name="Login" component={LoginScreen} />
    <Stack.Screen name="Register" component={RegisterScreen} />
  </Stack.Navigator>
);

const styles = StyleSheet.create({
  container: {
    flex: 1,
    paddingTop: 50,
    paddingHorizontal: 20,
    paddingBottom: 100,
    // height: 500,
    backgroundColor: '#fff',
    alignItems: 'center',
    justifyContent: 'center',
  },
  inputText: {
    width:"80%",
    fontSize:15,
    backgroundColor:"#e0e0e0",
    borderRadius:3,
    borderColor: "#1f1e33",
    borderWidth:1,
    height:50,
    marginBottom:20,
    paddingLeft: 15,
    paddingRight: 15,
  },
  belowInputButton: {
    width:"40%",
    backgroundColor:"#e0e0e0",
    borderRadius:3,
    height:50,
    alignItems:"center",
    justifyContent:"center",
    marginTop:40,
    marginBottom:20
  },
  subButton: {
    width:"40%",
    // backgroundColor:"#e0e0e0",
    borderRadius:3,
    height:50,
    alignItems:"center",
    justifyContent:"center",
    marginBottom:20
  },
  registerText: {
    fontSize: 16,
    color:"#1f1e33"
  },
  loginText: {
    fontSize: 16,
    color:"#1f1e33"
  },
  

})

export default AuthNavigator;