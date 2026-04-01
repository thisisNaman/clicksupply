"use client";

import { useEffect, useState } from "react";
import { listBrands, type Brand } from "@/lib/api";

/**
 * Hook to get the first (primary) brand for the current user.
 * Returns { brand, loading } — brand is null until loaded.
 */
export function useBrand() {
    const [brand, setBrand] = useState<Brand | null>(null);
    const [loading, setLoading] = useState(true);

    useEffect(() => {
        listBrands()
            .then((brands) => {
                if (brands.length > 0) setBrand(brands[0]);
            })
            .catch(() => { })
            .finally(() => setLoading(false));
    }, []);

    return { brand, loading };
}
