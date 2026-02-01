import { useEffect, useState } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { CheckCircle2, XCircle } from "lucide-react";
import { useBackendBaseUrl } from "@/hooks/useBackendBaseUrl";

interface Result {
  id: number;
  match_id: string;
  prediction_id: number;
  home_team: string;
  away_team: string;
  home_score: number;
  away_score: number;
  match_date: string;
}

interface PredictionResult {
  market_type: string;
  predicted_value: string;
  actual_value: string;
  is_correct: boolean;
}

export default function ResultsView() {
  const { apiBase, loading: baseLoading, error: baseError } = useBackendBaseUrl();
  const [results, setResults] = useState<Result[]>([]);
  const [predictionResults, setPredictionResults] = useState<Record<number, PredictionResult[]>>({});
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!apiBase) return;
    fetchResults();
  }, [apiBase]);

  const fetchResults = async () => {
    if (!apiBase) return;
    try {
      const response = await fetch(`${apiBase}/api/v1/results`);
      const data = await response.json();
      setResults(data);
      
      // Fetch prediction results for each result
      // In a real app, this would be a single API call
      const predResults: Record<number, PredictionResult[]> = {};
      for (const result of data) {
        // This is simplified - in reality you'd fetch from a proper endpoint
        predResults[result.id] = [];
      }
      setPredictionResults(predResults);
    } catch (error) {
      console.error("Error fetching results:", error);
    } finally {
      setLoading(false);
    }
  };

  const formatDate = (dateString: string) => {
    return new Date(dateString).toLocaleDateString("el-GR");
  };

  if (baseLoading || loading) {
    return <div className="p-6">Φόρτωση...</div>;
  }
  if (baseError) {
    return <div className="p-6 text-destructive">Σφάλμα backend: {baseError}</div>;
  }

  return (
    <div className="p-6 space-y-6">
      <Card>
        <CardHeader>
          <CardTitle>Αποτελέσματα Αγώνων</CardTitle>
        </CardHeader>
        <CardContent>
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Αγώνας</TableHead>
                <TableHead>Τελικό Σκορ</TableHead>
                <TableHead>Ημερομηνία</TableHead>
                <TableHead>Αποτέλεσμα</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {results.map((result) => (
                <TableRow key={result.id}>
                  <TableCell className="font-medium">
                    {result.home_team} vs {result.away_team}
                  </TableCell>
                  <TableCell>
                    <span className="text-lg font-bold">
                      {result.home_score} - {result.away_score}
                    </span>
                  </TableCell>
                  <TableCell>{formatDate(result.match_date)}</TableCell>
                  <TableCell>
                    <div className="flex gap-2">
                      {predictionResults[result.id]?.map((pr, idx) => (
                        <Badge
                          key={idx}
                          variant={pr.is_correct ? "default" : "destructive"}
                          className="flex items-center gap-1"
                        >
                          {pr.is_correct ? (
                            <CheckCircle2 className="h-3 w-3" />
                          ) : (
                            <XCircle className="h-3 w-3" />
                          )}
                          {pr.market_type}
                        </Badge>
                      ))}
                    </div>
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </CardContent>
      </Card>
    </div>
  );
}