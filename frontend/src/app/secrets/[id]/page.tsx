import ClientSecretPage from './ClientSecretPage';

export async function generateStaticParams() {
  return [{ id: '1' }, { id: '2' }];
}

export default function SecretDetailPage({ params }: { params: { id: string } }) {
  return <ClientSecretPage id={params.id} />;
}
