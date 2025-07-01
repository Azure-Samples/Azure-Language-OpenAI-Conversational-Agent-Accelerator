// Copyright (c) Microsoft Corporation.
// Licensed under the MIT License.
import './App.css';
import Chat from './Chat.jsx';

const App = () => {
  document.documentElement.lang = 'en';
  return (
    <div className="page-content-container">
      <h1>Contoso Outdoors GenAI Chat:</h1>
      <div className="chat-disclaimer">
        Disclaimer: This chat application uses AI to generate responses. Please verify the information provided.
      </div>
      <Chat/>
    </div>
  );
};

export default App;
