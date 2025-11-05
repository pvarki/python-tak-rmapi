import React from 'react';
import ReactDOM from 'react-dom/client';
import App from './App';

if(__USE_GLOBAL_CSS__ == true){
	import('./index.css');
}

ReactDOM.createRoot(document.getElementById('root') as HTMLElement).render(
	<React.StrictMode >
		<div className='dark m-4'>
			<App />
		</div>
	</React.StrictMode>,
);
