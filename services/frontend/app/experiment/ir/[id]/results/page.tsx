'use client';

import { useEffect } from 'react';
import { useParams, useRouter } from 'next/navigation';

export default function IRResultsRedirect() {
  const params = useParams();
  const router = useRouter();

  useEffect(() => {
    router.replace(`/experiment/${params.id}/results`);
  }, [params.id, router]);

  return null;
}
