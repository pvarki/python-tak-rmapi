import { Card, CardDescription, CardHeader, CardTitle } from './components/ui/card';

//Match the user data format /api gives
interface Props{
	data?: {

	}
}

export default ({data}: Props) => {

	return (
		<Card>
			<CardHeader>
				<CardTitle>TAK Component</CardTitle>
				<CardDescription>
					<p>This is a minimal federated component inside the TAK integration with shadcn + tailwindcss.</p>
					<p className='font-bold'>{data ? "This component received props." : "This component didn't receive any props"}</p>
				</CardDescription>
			</CardHeader>
		</Card>
	);
};
