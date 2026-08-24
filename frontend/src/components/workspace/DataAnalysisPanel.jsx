import React, { useRef, useState } from 'react';
import { 
  Send, 
  Paperclip, 
  X, 
  BarChart2, 
  Copy, 
  Check, 
  Sparkles, 
  FileSpreadsheet, 
  TrendingUp, 
  PieChart, 
  Database,
  ArrowRight,
  RefreshCw,
  Zap,
  ChevronDown,
  ChevronUp,
  Microscope,
  HelpCircle,
  FolderOpen,
  FileCode,
  Layers,
  Play,
  Terminal,
  Image,
  AlertCircle,
  Clock,
  Loader2,
  Edit3,
  RotateCcw,
  Download,
  Table,
  Search as SearchIcon,
  Activity,
  FileText,
  Maximize2,
  ExternalLink,
  Globe,
  BookOpen,
  UploadCloud,
  Trash2
} from 'lucide-react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import remarkMath from 'remark-math';
import rehypeKatex from 'rehype-katex';
import * as XLSX from 'xlsx';
import { useLanguage } from '../../contexts/LanguageContext';
import { safeFetch } from '../../utils/apiConfig';
import { formatMathAndMarkdown } from '../../utils/mathUtils';
import DynamicDataChart, { KPICardsGrid, DatasetHealthCard } from './DataCharts';
import { 
  generateStandaloneHTMLReport, 
  openReportInNewTab, 
  downloadHTMLReport, 
  downloadJupyterNotebook 
} from '../../utils/standaloneReportGenerator';


// Preloaded Demo Datasets inspired by ASTA
const DEMO_DATASETS = {
  air_quality: {
    name: 'air_quality_seasonal_daily.csv',
    label: 'Chất lượng không khí (AQI & Mùa)',
    content: `Date,Month,Season,AQI,PM25,PM10,SO2,NO2,CO,O3_8h,Temperature_C,Humidity_Pct,ConstantCol
2023-01-01,Jan,Winter,155,82.4,126.9,31.1,42.4,1.61,30.4,18.4,79,0
2023-01-02,Jan,Winter,162,78.2,124.0,33.5,47.8,1.78,32.0,12.7,42,0
2023-01-03,Jan,Winter,103,52.5,86.9,21.2,34.4,0.84,57.6,12.7,61,0
2023-01-04,Jan,Winter,165,83.3,131.4,33.9,53.9,1.79,41.0,14.8,44,0
2023-01-05,Jan,Winter,170,87.6,140.4,34.8,47.2,1.76,29.4,12.8,61,0
2023-01-06,Jan,Winter,121,57.5,90.0,23.3,32.7,1.09,43.0,18.4,42,0
2023-01-07,Jan,Winter,103,53.4,71.7,21.0,33.9,1.18,66.9,19.5,62,0
2023-01-08,Jan,Winter,159,74.7,111.1,31.3,50.7,1.7,42.8,17.0,42,0
2023-01-09,Jan,Winter,144,70.2,115.1,26.9,46.6,1.54,33.9,18.0,44,0
2023-01-10,Jan,Winter,,84.2,118.5,30.9,48.3,1.71,33.4,10.4,47,0
2023-01-11,Jan,Winter,105,51.7,86.0,19.3,29.2,1.12,66.1,10.5,66,0
2023-01-12,Jan,Winter,146,76.6,124.4,29.7,43.2,1.61,40.0,15.6,54,0
2023-01-13,Jan,Winter,145,70.1,109.3,29.4,41.6,1.36,40.5,16.3,67,0
2023-01-14,Jan,Winter,111,51.5,76.0,24.1,35.5,1.23,54.4,13.2,60,0
2023-01-15,Jan,Winter,165,,121.8,32.0,48.0,1.6,28.6,17.5,85,0
2023-01-16,Jan,Winter,110,58.6,80.8,21.8,31.6,1.3,61.8,16.0,73,0
2023-01-17,Jan,Winter,170,89.8,139.8,34.3,54.5,1.52,25.5,18.9,60,0
2023-01-18,Jan,Winter,168,85.8,129.8,33.2,50.3,1.74,34.0,17.2,80,0
2023-01-19,Jan,Winter,118,54.1,89.3,25.3,32.9,1.09,50.9,19.8,60,0
2023-01-20,Jan,Winter,166,87.4,137.3,33.6,47.0,1.71,41.8,16.5,84,0
2023-01-21,Jan,Winter,146,70.3,110.8,29.1,43.6,1.3,39.8,14.9,89,0
2023-01-22,Jan,Winter,141,66.1,90.5,27.9,38.9,1.3,46.3,18.2,58,0
2023-01-23,Jan,Winter,102,46.6,78.6,19.0,28.4,0.95,60.1,17.7,47,0
2023-01-24,Jan,Winter,168,87.2,129.4,32.3,45.6,1.49,32.8,16.9,43,0
2023-01-25,Jan,Winter,91,42.6,57.4,19.9,25.1,0.84,72.5,17.8,54,0
2023-01-26,Jan,Winter,115,59.1,80.9,21.8,31.8,1.14,50.1,11.4,52,0
2023-01-27,Jan,Winter,101,54.3,88.0,20.3,32.3,1.16,63.2,18.8,41,0
2023-01-28,Jan,Winter,140,67.4,91.2,27.7,39.7,1.49,42.1,18.8,52,0
2023-01-29,Jan,Winter,,48.1,79.0,18.5,25.0,1.12,68.0,11.5,81,0
2023-01-30,Jan,Winter,118,57.7,96.3,22.5,31.1,0.98,62.2,18.7,53,0
2023-01-31,Jan,Winter,123,62.1,84.2,24.9,41.7,1.11,49.6,10.3,86,0
2023-02-01,Feb,Winter,,69.3,103.0,26.3,42.3,1.58,34.2,16.8,88,0
2023-02-02,Feb,Winter,102,47.9,68.8,18.6,30.6,0.89,61.3,19.1,76,0
2023-02-03,Feb,Winter,161,79.0,117.3,32.5,43.3,1.71,28.7,16.4,55,0
2023-02-04,Feb,Winter,134,66.5,106.1,27.6,35.5,1.34,46.8,10.8,51,0
2023-02-05,Feb,Winter,163,84.2,127.1,34.1,44.0,1.43,28.6,11.1,45,0
2023-02-06,Feb,Winter,119,58.5,84.3,24.8,37.9,1.1,57.3,20.0,64,0
2023-02-07,Feb,Winter,157,81.0,123.0,29.7,49.7,1.47,34.2,19.2,45,0
2023-02-08,Feb,Winter,143,76.2,117.4,28.1,41.6,1.48,47.1,17.8,69,0
2023-02-09,Feb,Winter,155,81.3,121.5,30.0,48.2,1.62,40.7,14.5,74,0
2023-02-10,Feb,Winter,141,70.4,105.7,29.9,42.8,1.52,47.2,10.9,71,0
2023-02-11,Feb,Winter,112,60.2,99.0,20.9,28.9,1.21,53.1,10.9,70,0
2023-02-12,Feb,Winter,120,55.5,81.2,23.2,34.1,1.17,57.2,10.6,88,0
2023-02-13,Feb,Winter,98,53.0,73.7,18.1,26.5,1.03,53.8,16.7,55,0
2023-02-14,Feb,Winter,123,59.9,99.1,25.1,35.3,1.1,53.3,13.6,76,0
2023-02-15,Feb,Winter,167,82.0,127.0,34.2,54.2,1.86,39.2,12.2,85,0
2023-02-16,Feb,Winter,110,53.3,86.6,22.5,36.5,1.01,52.5,11.6,84,0
2023-02-17,Feb,Winter,103,48.1,71.7,19.0,25.9,0.95,59.9,15.6,50,0
2023-02-18,Feb,Winter,104,52.1,87.4,19.1,26.8,1.08,49.2,11.5,79,0
2023-02-19,Feb,Winter,107,49.9,79.9,21.6,31.9,1.04,62.8,11.0,64,0
2023-02-20,Feb,Winter,130,65.2,94.4,26.1,39.8,1.25,45.8,14.5,56,0
2023-02-21,Feb,Winter,124,60.2,83.3,23.7,36.8,1.41,60.3,11.4,51,0
2023-02-22,Feb,Winter,119,62.6,103.3,24.9,33.5,1.04,42.5,11.0,77,0
2023-02-23,Feb,Winter,132,62.6,95.2,26.6,42.0,1.25,37.3,11.5,61,0
2023-02-24,Feb,Winter,166,84.1,136.0,34.2,51.7,1.61,25.3,14.7,76,0
2023-02-25,Feb,Winter,97,,60.5,20.8,31.7,0.84,54.8,19.0,81,0
2023-02-26,Feb,Winter,168,80.2,120.7,31.8,51.5,1.67,33.5,18.8,69,0
2023-02-27,Feb,Winter,129,,107.2,26.8,36.9,1.36,45.2,15.7,53,0
2023-02-28,Feb,Winter,149,78.0,119.2,28.5,42.7,1.55,48.2,13.4,57,0
2023-03-01,Mar,Spring,97,51.2,73.3,18.6,26.0,0.99,62.1,27.0,71,0
2023-03-02,Mar,Spring,72,34.8,51.0,13.6,21.4,0.68,77.4,26.5,89,0
2023-03-03,Mar,Spring,77,34.6,44.6,15.8,25.4,0.6,78.7,20.9,71,0
2023-03-04,Mar,Spring,57,29.1,46.7,10.7,18.9,0.53,77.7,29.3,66,0
2023-03-05,Mar,Spring,91,41.7,60.6,19.7,23.3,1.1,54.4,25.6,78,0
2023-03-06,Mar,Spring,71,32.5,40.0,14.8,18.0,0.89,68.7,23.0,87,0
2023-03-07,Mar,Spring,30,17.8,17.3,5.6,12.0,0.29,92.0,27.8,83,0
2023-03-08,Mar,Spring,34,20.7,22.6,6.7,5.8,0.49,80.4,26.8,85,0
2023-03-09,Mar,Spring,77,37.9,49.5,15.5,18.9,0.78,69.5,23.7,56,0
2023-03-10,Mar,Spring,67,37.4,46.3,11.9,20.9,0.77,69.8,21.3,88,0
2023-03-11,Mar,Spring,24,13.9,21.9,3.0,10.4,0.19,100.1,26.9,57,0
2023-03-12,Mar,Spring,78,,60.9,13.8,23.6,0.81,59.5,20.9,58,0
2023-03-13,Mar,Spring,92,49.5,69.9,16.6,25.1,1.06,67.2,23.4,77,0
2023-03-14,Mar,Spring,59,29.5,52.9,10.0,20.6,0.6,67.6,21.1,78,0
2023-03-15,Mar,Spring,47,26.9,32.1,10.8,11.5,0.39,83.0,21.8,63,0
2023-03-16,Mar,Spring,61,26.4,40.8,13.2,19.6,0.54,81.2,22.9,90,0
2023-03-17,Mar,Spring,93,44.3,67.3,17.3,26.4,0.88,70.2,26.2,76,0
2023-03-18,Mar,Spring,93,48.5,67.3,18.6,31.6,0.89,72.7,24.2,77,0
2023-03-19,Mar,Spring,30,13.4,17.3,6.4,7.7,0.35,91.0,29.9,54,0
2023-03-20,Mar,Spring,41,24.1,39.2,9.1,9.1,0.51,91.4,24.8,77,0
2023-03-21,Mar,Spring,80,37.5,49.3,17.4,25.7,0.61,66.2,25.3,44,0
2023-03-22,Mar,Spring,82,42.5,70.2,16.7,21.4,0.86,77.2,21.8,57,0
2023-03-23,Mar,Spring,23,12.7,21.3,4.5,4.1,0.16,83.9,23.8,90,0
2023-03-24,Mar,Spring,30,16.5,32.1,5.9,11.5,0.27,86.1,23.5,82,0
2023-03-25,Mar,Spring,52,21.8,39.7,11.8,13.4,0.56,69.6,22.6,57,0
2023-03-26,Mar,Spring,56,25.7,41.1,13.0,14.4,0.41,69.0,27.9,63,0
2023-03-27,Mar,Spring,33,16.9,29.5,6.9,13.7,0.43,77.8,21.8,45,0
2023-03-28,Mar,Spring,49,,36.4,9.0,14.7,0.41,85.8,29.1,46,0
2023-03-29,Mar,Spring,79,34.6,43.6,17.6,22.3,0.85,70.3,28.2,71,0
2023-03-30,Mar,Spring,68,38.1,56.8,15.2,17.7,0.82,75.8,25.1,67,0
2023-03-31,Mar,Spring,100,52.4,82.0,20.0,32.9,1.16,57.7,24.9,51,0
2023-04-01,Apr,Spring,23,13.5,27.0,3.7,7.5,0.13,81.5,22.6,82,0
2023-04-02,Apr,Spring,29,14.0,23.1,5.6,6.0,0.26,92.6,27.3,75,0
2023-04-03,Apr,Spring,86,42.8,72.0,15.8,30.3,0.67,73.1,22.9,58,0
2023-04-04,Apr,Spring,26,16.1,14.6,6.7,4.3,0.24,96.2,23.8,65,0
2023-04-05,Apr,Spring,67,35.1,52.7,14.0,15.1,0.77,74.8,29.1,63,0
2023-04-06,Apr,Spring,73,33.4,48.6,13.1,19.6,0.88,72.6,28.4,50,0
2023-04-07,Apr,Spring,97,44.9,59.1,19.8,32.9,1.0,68.4,28.8,44,0
2023-04-08,Apr,Spring,28,14.3,28.7,7.5,8.7,0.33,98.7,22.3,70,0
2023-04-09,Apr,Spring,86,38.6,66.0,16.3,21.2,0.72,71.7,21.1,71,0
2023-04-10,Apr,Spring,47,27.7,44.6,11.1,9.8,0.62,84.4,21.6,46,0
2023-04-11,Apr,Spring,97,46.2,70.8,19.6,32.8,0.91,53.0,24.4,76,0
2023-04-12,Apr,Spring,54,28.5,36.3,10.1,20.6,0.36,77.9,27.0,61,0
2023-04-13,Apr,Spring,39,,24.6,7.1,9.0,0.29,76.7,28.6,74,0
2023-04-14,Apr,Spring,34,17.8,33.2,7.9,13.2,0.51,91.0,29.2,72,0
2023-04-15,Apr,Spring,21,9.7,6.4,5.6,8.9,0.29,98.0,29.2,53,0
2023-04-16,Apr,Spring,51,24.0,31.1,10.9,19.1,0.35,84.3,21.7,83,0
2023-04-17,Apr,Spring,24,9.2,20.6,4.9,5.5,0.14,85.8,22.3,62,0
2023-04-18,Apr,Spring,70,36.4,61.7,14.8,23.4,0.54,69.6,24.4,48,0
2023-04-19,Apr,Spring,88,45.5,68.3,16.3,30.2,0.89,66.0,20.5,76,0
2023-04-20,Apr,Spring,55,25.3,34.8,12.9,14.4,0.64,86.6,21.1,72,0
2023-04-21,Apr,Spring,71,31.8,51.7,15.3,24.3,0.61,77.4,21.2,40,0
2023-04-22,Apr,Spring,27,11.8,24.6,6.2,11.1,0.37,80.4,23.2,41,0
2023-04-23,Apr,Spring,51,25.7,42.3,11.4,15.3,0.31,89.4,25.8,56,0
2023-04-24,Apr,Spring,92,47.3,80.5,18.0,24.6,0.91,65.0,27.6,64,0
2023-04-25,Apr,Spring,40,24.8,31.7,9.2,10.2,0.38,88.8,25.7,58,0
2023-04-26,Apr,Spring,48,22.5,40.6,9.6,17.9,0.38,78.5,29.5,77,0
2023-04-27,Apr,Spring,36,16.6,17.7,8.4,13.2,0.2,84.8,22.2,48,0
2023-04-28,Apr,Spring,58,28.6,51.6,10.2,20.8,0.55,80.1,25.2,69,0
2023-04-29,Apr,Spring,56,23.8,30.3,12.3,19.7,0.39,76.0,29.6,47,0
2023-04-30,Apr,Spring,90,48.8,70.7,18.2,31.5,0.87,72.4,24.6,59,0
2023-05-01,May,Spring,90,46.7,75.1,16.2,30.8,0.82,72.9,28.1,73,0
2023-05-02,May,Spring,79,42.8,54.9,16.9,25.7,0.6,72.5,28.5,88,0
2023-05-03,May,Spring,72,37.7,64.0,13.3,17.0,0.75,71.3,23.3,56,0
2023-05-04,May,Spring,66,35.1,52.8,14.7,17.7,0.46,66.2,22.2,67,0
2023-05-05,May,Spring,50,21.7,25.3,10.0,15.3,0.38,70.6,21.0,67,0
2023-05-06,May,Spring,55,30.7,53.7,12.7,17.5,0.68,76.6,22.2,44,0
2023-05-07,May,Spring,84,44.4,72.0,18.0,24.9,0.83,58.2,29.6,44,0
2023-05-08,May,Spring,48,26.5,41.3,9.3,19.2,0.55,79.0,20.5,65,0
2023-05-09,May,Spring,68,38.2,61.4,13.4,18.0,0.87,67.3,21.6,50,0
2023-05-10,May,Spring,76,40.5,69.5,15.4,24.9,0.72,68.7,20.6,52,0
2023-05-11,May,Spring,48,19.0,24.6,11.0,14.8,0.58,71.8,20.9,76,0
2023-05-12,May,Spring,38,17.9,28.4,5.6,10.6,0.46,84.8,28.2,42,0
2023-05-13,May,Spring,97,46.3,74.5,19.2,29.6,1.11,57.1,26.5,77,0
2023-05-14,May,Spring,35,14.4,16.0,8.6,12.2,0.43,88.8,24.5,60,0
2023-05-15,May,Spring,76,38.1,64.8,14.4,21.7,0.84,67.8,23.3,73,0
2023-05-16,May,Spring,100,52.3,83.5,21.2,34.3,1.1,59.8,29.2,42,0
2023-05-17,May,Spring,96,44.0,66.4,17.8,30.4,1.1,70.3,23.5,49,0
2023-05-18,May,Spring,62,26.8,43.7,11.2,22.2,0.72,72.5,23.2,58,0
2023-05-19,May,Spring,96,51.3,78.5,19.1,28.3,0.9,66.9,24.8,69,0
2023-05-20,May,Spring,43,17.5,28.0,8.4,10.9,0.3,76.4,25.9,65,0
2023-05-21,May,Spring,87,46.8,80.0,18.6,23.5,0.72,59.9,24.8,69,0
2023-05-22,May,Spring,88,46.0,74.8,18.6,24.5,0.76,74.1,28.0,44,0
2023-05-23,May,Spring,24,8.1,8.2,5.0,3.5,0.41,87.3,22.6,90,0
2023-05-24,May,Spring,52,25.8,42.4,10.5,13.0,0.52,80.4,24.0,68,0
2023-05-25,May,Spring,33,17.2,28.4,7.9,7.5,0.51,80.7,28.3,69,0
2023-05-26,May,Spring,91,50.1,71.3,17.0,25.8,1.02,58.0,21.5,41,0
2023-05-27,May,Spring,67,34.7,51.3,12.6,20.0,0.52,77.6,27.0,90,0
2023-05-28,May,Spring,29,18.9,37.0,6.3,10.2,0.27,79.1,29.6,66,0
2023-05-29,May,Spring,96,43.5,62.7,17.4,32.5,0.78,71.2,29.5,41,0
2023-05-30,May,Spring,80,42.1,71.5,17.0,25.9,0.9,60.7,30.0,54,0
2023-05-31,May,Spring,89,42.6,70.9,18.7,25.4,0.79,66.6,27.5,68,0
2023-06-01,Jun,Summer,95,44.2,72.8,20.7,29.1,0.88,53.7,39.0,83,0
2023-06-02,Jun,Summer,29,12.1,11.5,4.0,4.8,0.09,92.0,42.5,67,0
2023-06-03,Jun,Summer,68,30.6,37.7,14.8,19.6,0.62,67.3,42.9,43,0
2023-06-04,Jun,Summer,96,44.7,71.8,20.2,25.8,1.1,67.0,38.0,81,0
2023-06-05,Jun,Summer,68,33.9,49.8,13.7,21.5,0.74,64.8,43.8,69,0
2023-06-06,Jun,Summer,65,28.4,51.5,13.1,24.4,0.85,70.7,37.2,61,0
2023-06-07,Jun,Summer,55,32.3,55.7,11.4,14.5,0.54,82.7,35.9,42,0
2023-06-08,Jun,Summer,54,31.6,40.3,11.3,16.6,0.43,81.1,37.6,85,0
2023-06-09,Jun,Summer,76,33.7,50.6,14.4,18.4,0.92,67.5,39.4,81,0
2023-06-10,Jun,Summer,21,9.7,5.9,2.9,7.1,0.12,100.3,44.7,47,0
2023-06-11,Jun,Summer,46,22.9,43.8,9.8,11.8,0.42,85.3,42.8,44,0
2023-06-12,Jun,Summer,85,44.1,57.9,15.7,27.2,0.67,60.2,42.9,50,0
2023-06-13,Jun,Summer,68,36.0,58.8,15.5,15.9,0.8,79.4,36.1,61,0
2023-06-14,Jun,Summer,89,45.2,61.2,17.1,25.6,0.86,58.0,37.0,53,0
2023-06-15,Jun,Summer,64,35.4,51.6,11.0,16.6,0.76,71.9,41.6,44,0
2023-06-16,Jun,Summer,81,42.2,66.9,17.1,23.5,0.95,62.3,39.2,87,0
2023-06-17,Jun,Summer,63,35.8,59.3,13.5,21.0,0.5,78.2,39.5,87,0
2023-06-18,Jun,Summer,86,47.6,76.3,19.1,22.9,0.79,72.6,35.3,72,0
2023-06-19,Jun,Summer,39,21.5,23.5,9.0,14.1,0.55,77.3,38.4,64,0
2023-06-20,Jun,Summer,,17.6,25.4,8.3,7.5,0.2,88.7,44.6,48,0
2023-06-21,Jun,Summer,72,37.3,65.4,14.1,21.8,0.65,75.2,35.2,57,0
2023-06-22,Jun,Summer,88,39.1,49.7,17.6,29.8,0.88,70.1,42.7,40,0
2023-06-23,Jun,Summer,72,32.3,54.8,15.6,26.3,0.61,72.4,35.5,42,0
2023-06-24,Jun,Summer,33,12.8,15.4,5.4,8.3,0.53,82.5,42.2,87,0
2023-06-25,Jun,Summer,91,42.2,55.0,19.2,23.7,1.02,67.0,41.0,76,0
2023-06-26,Jun,Summer,79,44.2,59.8,16.7,23.3,0.76,68.7,36.2,78,0
2023-06-27,Jun,Summer,96,48.9,83.1,20.4,25.9,0.84,60.5,35.6,82,0
2023-06-28,Jun,Summer,91,41.4,54.2,19.4,31.1,0.72,68.0,43.8,72,0
2023-06-29,Jun,Summer,76,35.0,44.4,15.4,19.9,0.91,66.8,38.3,63,0
2023-06-30,Jun,Summer,93,43.1,65.6,16.7,31.7,1.01,57.9,35.1,59,0
2023-07-01,Jul,Summer,49,22.4,41.6,9.2,12.0,0.53,76.2,38.7,77,0
2023-07-02,Jul,Summer,99,47.4,78.2,19.8,29.5,0.89,59.8,37.0,75,0
2023-07-03,Jul,Summer,21,10.7,8.6,3.4,3.3,0.07,100.9,35.6,59,0
2023-07-04,Jul,Summer,64,30.1,53.5,11.4,17.2,0.66,68.5,44.8,84,0
2023-07-05,Jul,Summer,57,32.6,50.5,12.7,12.9,0.76,70.6,37.3,86,0
2023-07-06,Jul,Summer,36,23.0,30.4,7.4,7.8,0.5,80.1,43.8,57,0
2023-07-07,Jul,Summer,75,38.9,56.8,15.7,24.7,0.91,68.5,41.5,88,0
2023-07-08,Jul,Summer,31,19.2,19.6,5.2,12.3,0.31,96.9,35.0,40,0
2023-07-09,Jul,Summer,92,47.7,77.9,17.2,28.6,0.85,60.1,37.6,51,0
2023-07-10,Jul,Summer,52,28.6,47.0,12.3,15.9,0.59,85.4,35.9,70,0
2023-07-11,Jul,Summer,22,13.1,12.1,4.9,7.9,0.04,97.7,42.7,90,0
2023-07-12,Jul,Summer,79,40.6,52.7,16.9,25.2,0.88,59.4,44.6,87,0
2023-07-13,Jul,Summer,95,43.5,64.3,20.7,24.9,0.99,55.7,36.3,62,0
2023-07-14,Jul,Summer,96,44.3,72.4,17.9,30.9,0.94,71.1,35.5,59,0
2023-07-15,Jul,Summer,56,31.7,51.0,10.0,12.0,0.65,82.6,35.4,80,0
2023-07-16,Jul,Summer,21,12.4,17.4,4.2,2.3,0.14,94.8,37.8,89,0
2023-07-17,Jul,Summer,41,22.7,29.7,9.7,16.9,0.5,81.7,36.9,48,0
2023-07-18,Jul,Summer,96,51.7,78.1,17.9,32.5,0.98,55.7,37.4,86,0
2023-07-19,Jul,Summer,27,16.1,29.6,6.4,7.6,0.27,98.6,42.9,83,0
2023-07-20,Jul,Summer,21,,24.0,5.7,10.6,0.16,84.5,42.8,58,0
2023-07-21,Jul,Summer,34,20.7,37.8,8.4,12.0,0.53,82.0,39.8,63,0
2023-07-22,Jul,Summer,62,26.2,48.1,11.3,21.7,0.48,68.1,39.8,76,0
2023-07-23,Jul,Summer,76,36.3,62.6,15.7,22.5,0.95,60.8,42.2,60,0
2023-07-24,Jul,Summer,89,46.7,78.8,17.5,30.3,0.79,64.4,42.0,73,0
2023-07-25,Jul,Summer,45,20.4,29.8,10.6,12.2,0.63,87.1,41.3,77,0
2023-07-26,Jul,Summer,23,9.1,4.4,3.1,3.2,0.15,85.1,36.0,62,0
2023-07-27,Jul,Summer,56,26.0,37.7,11.7,17.8,0.53,83.6,38.2,79,0
2023-07-28,Jul,Summer,67,36.5,62.0,12.3,16.0,0.56,63.8,38.0,69,0
2023-07-29,Jul,Summer,39,15.0,29.3,8.1,14.8,0.4,81.7,41.8,58,0
2023-07-30,Jul,Summer,51,30.4,43.5,9.7,13.6,0.45,77.8,37.9,59,0
2023-07-31,Jul,Summer,40,20.0,24.8,6.1,10.9,0.55,88.5,44.7,57,0
2023-08-01,Aug,Summer,51,30.4,39.3,8.7,11.2,0.66,77.0,35.5,47,0
2023-08-02,Aug,Summer,36,13.8,23.8,8.7,10.2,0.52,95.2,42.9,73,0
2023-08-03,Aug,Summer,46,27.3,38.7,9.6,17.0,0.62,89.6,42.9,60,0
2023-08-04,Aug,Summer,46,18.1,23.5,8.3,13.7,0.55,79.2,39.2,40,0
2023-08-05,Aug,Summer,64,29.2,36.9,12.3,22.4,0.63,64.4,40.7,76,0
2023-08-06,Aug,Summer,35,15.2,14.8,5.9,13.4,0.19,95.2,37.9,87,0
2023-08-07,Aug,Summer,80,36.5,47.1,15.1,24.4,0.73,68.9,43.5,82,0
2023-08-08,Aug,Summer,63,28.2,44.7,14.3,14.2,0.79,80.2,37.5,76,0
2023-08-09,Aug,Summer,95,50.1,67.0,20.1,32.8,1.02,70.3,39.2,77,0
2023-08-10,Aug,Summer,59,27.3,45.2,12.1,16.9,0.63,84.2,40.7,83,0
2023-08-11,Aug,Summer,23,14.0,12.5,3.2,2.7,0.16,99.8,39.5,60,0
2023-08-12,Aug,Summer,30,15.9,16.8,4.4,7.8,0.38,89.9,39.4,76,0
2023-08-13,Aug,Summer,22,12.5,13.3,3.3,9.0,0.03,87.5,36.9,86,0
2023-08-14,Aug,Summer,49,26.9,31.8,10.4,12.3,0.49,71.6,43.0,45,0
2023-08-15,Aug,Summer,51,25.9,44.5,10.6,18.5,0.39,85.0,43.5,81,0
2023-08-16,Aug,Summer,88,47.5,70.8,17.6,23.9,0.81,55.2,38.2,40,0
2023-08-17,Aug,Summer,57,26.2,44.3,10.2,17.8,0.59,79.1,40.6,48,0
2023-08-18,Aug,Summer,34,12.7,14.1,7.3,7.9,0.48,82.2,43.2,56,0
2023-08-19,Aug,Summer,84,42.2,63.2,17.6,28.7,0.89,75.8,37.6,59,0
2023-08-20,Aug,Summer,68,29.0,35.2,13.2,19.9,0.8,63.3,40.9,78,0
2023-08-21,Aug,Summer,40,17.4,33.4,9.5,13.1,0.47,83.3,41.8,50,0
2023-08-22,Aug,Summer,79,40.8,67.1,16.9,24.5,0.95,66.9,39.2,80,0
2023-08-23,Aug,Summer,80,44.1,67.3,17.8,22.7,0.73,73.5,43.6,43,0
2023-08-24,Aug,Summer,25,14.2,16.4,6.0,10.1,0.29,85.5,39.1,52,0
2023-08-25,Aug,Summer,98,47.2,80.1,21.4,27.5,1.0,63.5,36.5,46,0
2023-08-26,Aug,Summer,90,46.8,69.7,17.3,29.8,0.95,68.3,42.7,40,0
2023-08-27,Aug,Summer,28,11.3,17.9,5.4,13.0,0.21,84.8,42.9,75,0
2023-08-28,Aug,Summer,27,18.3,32.9,4.4,9.6,0.17,82.6,36.1,53,0
2023-08-29,Aug,Summer,55,25.1,43.6,10.2,18.8,0.68,80.6,37.1,69,0
2023-08-30,Aug,Summer,64,29.7,43.3,14.2,24.1,0.81,69.8,40.0,44,0
2023-08-31,Aug,Summer,58,27.8,32.0,13.6,17.1,0.45,75.0,43.8,89,0
2023-09-01,Sep,Autumn,98,45.0,62.0,18.9,26.8,0.97,57.9,28.5,52,0
2023-09-02,Sep,Autumn,125,66.8,109.8,23.6,38.6,1.21,42.1,22.3,51,0
2023-09-03,Sep,Autumn,123,64.5,95.1,24.5,38.6,1.39,60.0,22.8,45,0
2023-09-04,Sep,Autumn,81,40.4,70.5,16.5,27.8,0.75,72.5,29.5,71,0
2023-09-05,Sep,Autumn,109,53.6,81.8,20.5,35.5,0.97,50.0,25.9,49,0
2023-09-06,Sep,Autumn,124,63.5,85.9,24.1,35.8,1.27,42.6,22.5,46,0
2023-09-07,Sep,Autumn,52,28.2,34.5,10.6,19.5,0.44,76.1,22.6,52,0
2023-09-08,Sep,Autumn,73,41.0,60.2,15.6,20.7,0.62,78.8,24.0,46,0
2023-09-09,Sep,Autumn,110,53.5,73.2,21.9,37.1,1.12,56.9,28.7,79,0
2023-09-10,Sep,Autumn,70,39.3,64.9,12.8,16.5,0.77,73.8,23.9,86,0
2023-09-11,Sep,Autumn,87,39.0,51.2,17.2,29.5,0.71,68.7,28.6,49,0
2023-09-12,Sep,Autumn,67,31.1,53.7,12.2,23.3,0.62,67.6,24.9,90,0
2023-09-13,Sep,Autumn,107,56.9,80.3,21.9,30.1,1.15,60.8,27.8,63,0
2023-09-14,Sep,Autumn,103,50.9,77.2,19.0,26.3,1.15,51.4,29.1,40,0
2023-09-15,Sep,Autumn,122,60.3,96.8,25.2,36.8,1.41,53.0,29.0,85,0
2023-09-16,Sep,Autumn,68,31.6,40.4,15.4,21.0,0.86,78.9,24.6,83,0
2023-09-17,Sep,Autumn,105,,69.1,19.3,29.2,1.03,48.5,27.0,53,0
2023-09-18,Sep,Autumn,68,34.4,47.7,14.5,24.2,0.74,79.2,28.2,69,0
2023-09-19,Sep,Autumn,95,46.5,73.7,20.6,25.6,1.15,70.9,21.2,52,0
2023-09-20,Sep,Autumn,50,27.3,36.9,8.6,16.2,0.52,80.0,23.3,72,0
2023-09-21,Sep,Autumn,109,50.2,69.1,20.1,28.2,0.96,63.9,21.6,59,0
2023-09-22,Sep,Autumn,91,47.0,72.3,18.9,23.6,0.94,53.8,28.3,89,0
2023-09-23,Sep,Autumn,112,57.4,84.0,21.9,35.5,1.0,47.8,22.8,80,0
2023-09-24,Sep,Autumn,103,47.9,66.3,19.6,28.3,1.05,60.1,20.5,87,0
2023-09-25,Sep,Autumn,108,52.8,71.8,22.8,33.0,0.95,59.5,25.3,68,0
2023-09-26,Sep,Autumn,127,68.2,99.1,27.2,37.3,1.4,54.1,21.4,71,0
2023-09-27,Sep,Autumn,102,48.8,65.7,20.1,27.0,1.21,57.3,29.3,90,0
2023-09-28,Sep,Autumn,65,28.0,44.1,14.3,17.9,0.78,80.3,29.8,43,0
2023-09-29,Sep,Autumn,96,43.7,72.0,19.5,30.7,0.79,71.5,24.1,77,0
2023-09-30,Sep,Autumn,62,30.1,46.5,11.8,15.6,0.76,82.6,24.6,49,0
2023-10-01,Oct,Autumn,85,37.6,51.6,15.8,23.2,1.03,68.7,26.4,75,0
2023-10-02,Oct,Autumn,126,67.9,102.4,23.3,41.2,1.1,47.3,26.2,68,0
2023-10-03,Oct,Autumn,66,30.5,42.8,15.0,16.6,0.78,66.6,24.1,46,0
2023-10-04,Oct,Autumn,51,20.7,37.0,8.4,12.4,0.49,78.3,21.8,49,0
2023-10-05,Oct,Autumn,106,56.3,90.7,21.5,34.5,1.23,67.2,22.5,54,0
2023-10-06,Oct,Autumn,101,54.8,88.2,21.3,27.2,1.04,68.3,22.1,86,0
2023-10-07,Oct,Autumn,71,37.2,46.1,12.5,18.1,0.86,79.0,28.6,66,0
2023-10-08,Oct,Autumn,54,25.4,43.3,11.6,15.5,0.43,78.2,21.8,74,0
2023-10-09,Oct,Autumn,51,26.9,39.4,10.7,19.4,0.6,74.8,25.5,76,0
2023-10-10,Oct,Autumn,127,65.7,90.4,24.2,36.3,1.38,44.1,28.1,82,0
2023-10-11,Oct,Autumn,111,52.8,78.7,21.5,33.7,1.04,61.3,28.4,78,0
2023-10-12,Oct,Autumn,114,53.8,76.2,23.4,38.6,1.07,57.0,21.0,56,0
2023-10-13,Oct,Autumn,122,60.2,84.7,22.8,39.5,1.39,58.0,24.2,41,0
2023-10-14,Oct,Autumn,66,32.9,40.1,15.1,20.7,0.78,66.2,24.4,50,0
2023-10-15,Oct,Autumn,86,46.5,67.4,15.8,22.6,0.76,74.3,21.2,48,0
2023-10-16,Oct,Autumn,127,66.4,102.5,25.4,40.2,1.18,52.0,27.2,74,0
2023-10-17,Oct,Autumn,56,32.6,51.6,11.5,20.7,0.61,73.6,28.2,78,0
2023-10-18,Oct,Autumn,106,53.5,77.1,20.7,31.2,1.04,66.9,27.7,45,0
2023-10-19,Oct,Autumn,62,28.4,40.4,10.6,16.2,0.5,72.9,27.1,59,0
2023-10-20,Oct,Autumn,90,40.9,59.9,17.1,24.2,1.01,59.7,24.8,76,0
2023-10-21,Oct,Autumn,100,48.7,63.8,19.7,33.5,0.87,65.6,25.6,58,0
2023-10-22,Oct,Autumn,117,55.2,81.5,24.9,31.2,1.14,49.7,26.8,79,0
2023-10-23,Oct,Autumn,111,52.4,73.3,22.4,37.0,1.22,47.0,21.7,81,0
2023-10-24,Oct,Autumn,94,46.4,76.9,17.1,31.5,0.83,53.4,28.7,47,0
2023-10-25,Oct,Autumn,100,46.7,62.1,21.7,29.8,1.14,63.6,21.2,49,0
2023-10-26,Oct,Autumn,120,59.4,90.7,22.1,35.0,1.25,55.0,22.3,86,0
2023-10-27,Oct,Autumn,104,56.4,91.8,20.5,31.9,0.84,56.0,22.4,52,0
2023-10-28,Oct,Autumn,77,36.1,60.9,15.3,23.0,0.85,63.2,21.8,77,0
2023-10-29,Oct,Autumn,77,41.3,62.5,13.9,22.3,0.89,72.4,21.1,63,0
2023-10-30,Oct,Autumn,50,29.2,41.0,9.3,16.9,0.67,74.8,25.3,83,0
2023-10-31,Oct,Autumn,119,57.9,81.0,24.3,30.7,1.3,60.6,22.1,88,0
2023-11-01,Nov,Autumn,127,62.1,99.2,26.8,33.9,1.25,59.2,26.2,76,0
2023-11-02,Nov,Autumn,106,50.2,80.3,21.4,28.5,1.26,65.2,23.6,88,0
2023-11-03,Nov,Autumn,105,56.4,82.2,21.2,33.6,1.2,59.1,23.7,68,0
2023-11-04,Nov,Autumn,66,30.9,56.2,11.7,17.1,0.79,64.5,26.1,75,0
2023-11-05,Nov,Autumn,125,61.6,93.9,26.6,42.4,1.28,48.1,28.2,56,0
2023-11-06,Nov,Autumn,130,61.4,85.5,26.8,37.8,1.2,38.4,26.6,57,0
2023-11-07,Nov,Autumn,60,33.7,54.8,12.1,15.8,0.44,69.6,21.6,75,0
2023-11-08,Nov,Autumn,54,27.8,34.6,11.5,19.1,0.37,80.2,24.9,71,0
2023-11-09,Nov,Autumn,110,51.4,77.0,22.2,29.5,1.3,54.7,27.9,55,0
2023-11-10,Nov,Autumn,71,34.4,44.0,13.8,25.7,0.71,76.0,20.5,42,0
2023-11-11,Nov,Autumn,73,35.6,57.7,15.3,21.9,0.84,63.7,23.0,82,0
2023-11-12,Nov,Autumn,86,40.5,54.4,18.2,29.8,0.85,68.6,29.2,42,0
2023-11-13,Nov,Autumn,67,37.3,46.2,14.3,15.3,0.83,67.0,26.2,51,0
2023-11-14,Nov,Autumn,118,58.4,82.3,25.0,33.0,1.26,54.6,28.7,50,0
2023-11-15,Nov,Autumn,93,48.4,70.2,18.3,22.9,0.98,61.8,24.7,52,0
2023-11-16,Nov,Autumn,115,54.6,75.3,23.5,33.6,1.13,54.9,29.1,81,0
2023-11-17,Nov,Autumn,86,46.6,69.6,18.6,21.6,1.04,57.3,28.2,71,0
2023-11-18,Nov,Autumn,76,39.5,58.5,16.0,18.3,0.65,73.8,23.6,75,0
2023-11-19,Nov,Autumn,122,58.5,83.5,25.6,31.6,1.05,46.5,25.1,86,0
2023-11-20,Nov,Autumn,50,23.6,44.9,10.1,16.5,0.59,82.7,22.1,69,0
2023-11-21,Nov,Autumn,79,36.6,46.2,16.8,21.7,0.67,58.8,23.3,72,0
2023-11-22,Nov,Autumn,90,43.6,58.9,19.0,28.8,0.77,56.4,29.8,63,0
2023-11-23,Nov,Autumn,84,45.9,59.7,16.8,20.8,0.75,69.8,26.6,62,0
2023-11-24,Nov,Autumn,93,51.0,78.0,20.4,30.1,0.91,55.1,29.2,82,0
2023-11-25,Nov,Autumn,97,45.5,66.0,19.6,33.3,1.02,63.6,24.4,83,0
2023-11-26,Nov,Autumn,50,25.7,39.3,10.5,16.7,0.39,89.3,21.8,50,0
2023-11-27,Nov,Autumn,69,30.9,43.5,13.7,21.7,0.62,65.8,24.8,43,0
2023-11-28,Nov,Autumn,61,28.1,33.9,10.3,19.1,0.78,83.4,24.9,65,0
2023-11-29,Nov,Autumn,106,50.3,79.7,22.3,35.6,1.13,52.3,27.8,64,0
2023-11-30,Nov,Autumn,68,38.0,51.1,13.7,17.6,0.71,77.4,28.5,43,0
2023-12-01,Dec,Winter,159,83.7,119.0,31.5,45.1,1.44,45.6,15.8,66,0
2023-12-02,Dec,Winter,143,74.7,120.8,30.0,40.4,1.29,36.2,16.2,40,0
2023-12-03,Dec,Winter,163,85.9,138.7,33.0,49.8,1.61,26.9,10.1,87,0
2023-12-04,Dec,Winter,97,51.5,70.2,19.0,29.3,0.92,56.3,16.1,68,0
2023-12-05,Dec,Winter,126,63.2,100.6,23.8,40.0,1.3,53.3,12.1,89,0
2023-12-06,Dec,Winter,144,72.3,101.3,30.5,41.5,1.55,41.2,13.4,78,0
2023-12-07,Dec,Winter,156,73.7,120.4,30.8,50.0,1.6,38.0,19.9,70,0
2023-12-08,Dec,Winter,110,50.7,69.4,23.2,29.4,1.26,47.6,18.2,69,0
2023-12-09,Dec,Winter,166,86.7,137.8,33.7,49.8,1.72,29.6,11.1,71,0
2023-12-10,Dec,Winter,127,66.9,96.9,27.2,35.0,1.39,43.5,17.6,73,0
2023-12-11,Dec,Winter,129,65.7,94.7,27.6,38.4,1.35,47.0,12.6,57,0
2023-12-12,Dec,Winter,99,53.7,79.9,19.0,30.5,0.99,54.3,12.0,66,0
2023-12-13,Dec,Winter,107,57.4,96.0,21.2,30.5,1.1,62.0,11.8,40,0
2023-12-14,Dec,Winter,161,80.0,116.6,34.1,51.6,1.42,35.1,15.8,60,0
2023-12-15,Dec,Winter,108,,85.0,20.6,28.4,1.01,57.0,11.4,70,0
2023-12-16,Dec,Winter,92,50.7,70.4,19.0,26.0,0.76,57.3,18.0,71,0
2023-12-17,Dec,Winter,132,69.9,114.1,24.4,42.1,1.49,48.2,13.6,69,0
2023-12-18,Dec,Winter,154,73.6,100.6,29.7,49.8,1.69,45.8,10.7,82,0
2023-12-19,Dec,Winter,97,50.3,71.1,17.7,31.4,0.98,58.4,17.9,52,0
2023-12-20,Dec,Winter,113,55.3,84.5,22.5,33.5,1.23,55.4,19.1,46,0
2023-12-21,Dec,Winter,138,69.6,103.3,27.0,41.7,1.2,46.5,13.5,83,0
2023-12-22,Dec,Winter,157,74.6,109.9,30.0,47.4,1.52,38.3,12.3,83,0
2023-12-23,Dec,Winter,122,,82.6,25.2,36.8,1.22,42.1,13.8,85,0
2023-12-24,Dec,Winter,94,46.3,77.2,20.8,32.0,0.74,59.9,17.1,88,0
2023-12-25,Dec,Winter,94,51.4,67.8,17.8,26.9,1.07,61.9,11.4,42,0
2023-12-26,Dec,Winter,92,48.5,67.4,20.3,23.9,0.94,58.6,19.7,75,0
2023-12-27,Dec,Winter,128,67.3,92.8,25.5,34.6,1.16,41.8,17.1,47,0
2023-12-28,Dec,Winter,123,66.2,90.6,25.3,34.2,1.16,48.9,17.8,86,0
2023-12-29,Dec,Winter,120,55.8,77.1,24.5,38.5,1.12,42.5,19.1,51,0
2023-12-30,Dec,Winter,138,68.0,109.1,27.0,42.5,1.22,37.6,15.0,48,0
2023-12-31,Dec,Winter,140,74.2,102.9,26.0,45.2,1.56,38.1,16.3,40,0`
  },
  titanic: {
    name: 'titanic_survival_100.csv',
    label: 'Titanic Survival Dataset',
    content: `PassengerId,Survived,Pclass,Sex,Age,SibSp,Parch,Fare,Embarked,Class_Category
1,1,1,male,58.3,0,0,149.38,C,First Class
2,1,1,male,47.4,0,1,77.6,C,First Class
3,0,3,male,59.3,0,0,15.52,S,Third Class
4,0,2,male,47.5,0,0,139.84,S,Second Class
5,1,1,male,12.2,1,1,128.05,S,First Class
6,0,1,male,16.8,0,0,286.34,C,First Class
7,1,1,female,25.0,0,0,218.12,C,First Class
8,1,3,female,36.6,8,0,34.98,Q,Third Class
9,0,3,male,,0,0,75.61,,Third Class
10,1,3,female,56.3,0,0,61.29,Q,Third Class
11,1,2,female,39.1,0,0,72.8,C,Second Class
12,1,3,female,49.4,1,0,53.65,S,Third Class
13,1,1,female,45.9,4,2,198.68,C,First Class
14,1,2,female,50.8,0,0,10.48,C,Second Class
15,1,3,female,,4,2,7.67,S,Third Class
16,1,3,female,64.8,0,0,42.54,C,Third Class
17,0,2,male,22.1,0,0,56.04,C,Second Class
18,0,1,female,13.8,1,1,165.83,Q,First Class
19,0,2,female,47.5,0,1,56.49,C,Second Class
20,1,3,female,36.5,0,0,51.74,S,Third Class
21,0,3,male,,0,0,79.64,C,Third Class
22,1,1,female,1.4,0,0,183.31,Q,First Class
23,0,1,male,28.6,8,1,212.7,,First Class
24,0,3,male,30.4,0,0,45.07,C,Third Class
25,1,1,female,26.3,0,0,112.75,Q,First Class
26,0,3,male,,0,0,6.33,C,Third Class
27,0,3,male,55.8,1,0,98.82,Q,Third Class
28,0,2,male,,0,0,18.54,C,Second Class
29,0,2,male,9.3,1,0,142.4,Q,Second Class
30,1,1,female,9.9,1,0,114.37,C,First Class
31,1,3,female,,0,2,21.81,Q,Third Class
32,0,3,male,58.6,0,0,11.18,Q,Third Class
33,1,1,female,18.9,0,0,38.86,C,First Class
34,0,3,male,41.4,0,0,47.52,Q,Third Class
35,1,2,female,67.5,0,0,86.84,C,Second Class
36,0,2,male,32.7,1,0,149.66,C,Second Class
37,1,1,female,68.0,0,0,244.69,Q,First Class
38,0,3,female,30.7,1,0,81.82,S,Third Class
39,0,3,male,53.6,0,1,65.09,S,Third Class
40,0,3,male,,0,0,76.59,S,Third Class
41,0,2,male,22.4,0,0,187.43,Q,Second Class
42,1,1,female,22.7,0,0,47.58,C,First Class
43,1,3,female,36.6,0,3,77.34,C,Third Class
44,0,1,male,,0,0,184.33,C,First Class
45,1,1,male,41.8,0,0,247.23,S,First Class
46,0,2,male,57.4,0,0,196.63,Q,Second Class
47,1,1,male,63.3,0,1,196.27,S,First Class
48,1,3,female,59.2,2,0,82.08,S,Third Class
49,1,2,female,40.4,0,1,158.77,S,Second Class
50,0,3,female,60.3,0,0,9.8,C,Third Class
51,1,3,male,1.8,0,0,98.88,C,Third Class
52,0,2,female,12.0,0,1,193.14,S,Second Class
53,1,1,male,18.7,0,1,146.76,S,First Class
54,0,2,male,34.6,3,0,195.86,S,Second Class
55,1,3,male,49.7,1,1,49.51,C,Third Class
56,1,3,female,11.4,0,0,86.39,C,Third Class
57,0,3,male,30.7,1,1,23.17,C,Third Class
58,0,3,female,22.8,2,0,80.12,S,Third Class
59,1,3,female,12.7,0,0,6.24,C,Third Class
60,0,2,male,2.8,1,0,104.49,Q,Second Class
61,0,3,male,5.8,0,0,84.62,C,Third Class
62,1,3,female,17.6,0,0,37.55,S,Third Class
63,0,2,male,14.3,0,1,20.55,C,Second Class
64,0,1,male,65.3,0,2,117.21,S,First Class
65,1,2,female,15.8,3,0,96.43,Q,Second Class
66,1,3,female,59.3,0,0,5.55,C,Third Class
67,0,3,male,39.9,0,0,13.22,S,Third Class
68,0,3,female,25.4,0,1,83.54,Q,Third Class
69,0,3,male,18.4,0,0,89.75,S,Third Class
70,0,2,male,61.1,0,0,108.25,Q,Second Class
71,1,3,female,57.4,0,2,42.85,C,Third Class
72,1,1,male,44.1,0,0,240.64,C,First Class
73,1,3,female,36.0,0,0,95.76,C,Third Class
74,0,1,male,46.6,0,2,271.68,S,First Class
75,0,2,male,66.2,0,4,120.99,S,Second Class
76,0,3,female,14.9,0,0,77.87,S,Third Class
77,1,2,female,11.7,2,1,145.21,Q,Second Class
78,0,3,female,63.7,1,2,48.43,,Third Class
79,1,1,female,12.2,0,4,220.45,S,First Class
80,0,3,male,45.0,0,0,60.61,S,Third Class
81,0,3,male,12.2,0,2,70.81,C,Third Class
82,1,3,female,1.9,0,0,11.13,C,Third Class
83,0,3,male,14.0,1,0,79.14,S,Third Class
84,0,3,male,23.3,0,0,9.76,C,Third Class
85,0,3,male,38.6,0,0,56.48,C,Third Class
86,1,1,male,54.8,0,0,94.12,S,First Class
87,0,3,male,8.6,0,1,50.59,S,Third Class
88,0,2,male,20.9,0,1,130.68,C,Second Class
89,0,3,male,1.9,8,0,20.74,C,Third Class
90,1,3,female,12.8,0,0,59.77,C,Third Class
91,0,3,male,31.7,1,0,33.91,C,Third Class
92,1,2,female,,0,0,187.15,C,Second Class
93,1,3,female,27.4,0,1,84.06,Q,Third Class
94,1,1,male,67.7,0,0,255.53,Q,First Class
95,0,3,male,32.2,0,1,10.86,C,Third Class
96,1,2,male,8.2,4,1,123.03,C,Second Class
97,1,3,male,5.0,0,0,57.23,C,Third Class
98,1,3,female,50.5,0,1,52.43,S,Third Class
99,1,1,male,63.3,8,0,288.29,C,First Class
100,0,3,male,55.6,0,0,25.88,S,Third Class`
  },
  cell_biology: {
    name: 'tabula_macrophages_expression_50.csv',
    label: 'Tabula Sapiens - Macrophages Expression',
    content: `Cell_ID,Tissue,Subpopulation,M1_Score,M2_Score,CD68_Exp,CD163_Exp,TNF_Exp,IL10_Exp,Status
Cell_001,Kidney,Intermediate,0.51,0.54,8.1,3.1,2.2,4.8,Transitioning
Cell_002,Liver,M1-skewed,0.92,0.22,8.0,1.6,7.3,0.8,Pro-inflammatory
Cell_003,Liver,M1-skewed,0.88,0.21,7.8,1.7,6.3,1.1,Pro-inflammatory
Cell_004,Lung,M1-skewed,0.97,0.22,7.8,1.7,5.4,0.9,Pro-inflammatory
Cell_005,Kidney,M1-skewed,0.75,0.06,9.4,1.4,5.8,0.6,Pro-inflammatory
Cell_006,Brain,M2-skewed,0.2,0.81,6.7,7.6,1.5,6.7,Anti-inflammatory
Cell_007,Heart,M1-skewed,0.74,0.29,8.7,1.5,7.5,1.5,Pro-inflammatory
Cell_008,Heart,Intermediate,0.31,0.61,6.7,4.1,2.9,2.6,Transitioning
Cell_009,Brain,M1-skewed,0.93,0.17,7.5,2.1,6.6,1.1,Pro-inflammatory
Cell_010,Liver,M2-skewed,0.29,0.97,7.5,8.4,1.6,7.0,Anti-inflammatory
Cell_011,Heart,Intermediate,0.56,0.34,6.7,3.8,2.9,4.2,Transitioning
Cell_012,Heart,Intermediate,0.66,0.44,7.1,3.1,4.8,3.2,Transitioning
Cell_013,Kidney,Intermediate,0.64,0.69,7.6,4.5,3.6,3.7,Transitioning
Cell_014,Kidney,M2-skewed,0.09,0.76,7.3,8.0,2.0,5.6,Anti-inflammatory
Cell_015,Lung,M1-skewed,0.83,0.06,8.5,2.5,5.4,1.2,Pro-inflammatory
Cell_016,Heart,M2-skewed,0.27,0.92,6.9,8.2,0.8,4.7,Anti-inflammatory
Cell_017,Liver,Intermediate,0.41,0.58,6.5,4.9,4.6,2.1,Transitioning
Cell_018,Kidney,M2-skewed,0.08,0.85,6.7,7.3,1.0,5.5,Anti-inflammatory
Cell_019,Kidney,Intermediate,,0.64,7.7,3.4,3.5,4.9,Transitioning
Cell_020,Brain,M1-skewed,0.73,0.28,8.5,0.6,6.4,0.5,Pro-inflammatory
Cell_021,Brain,M1-skewed,0.94,0.28,8.7,1.3,6.6,1.2,Pro-inflammatory
Cell_022,Heart,M2-skewed,0.16,0.71,7.0,8.5,0.8,5.3,Anti-inflammatory
Cell_023,Heart,Intermediate,0.46,0.46,8.4,5.7,2.6,3.7,Transitioning
Cell_024,Kidney,M2-skewed,0.28,0.77,7.0,8.2,1.7,5.3,Anti-inflammatory
Cell_025,Heart,M2-skewed,0.04,1.0,6.3,7.2,1.2,5.9,Anti-inflammatory
Cell_026,Kidney,Intermediate,0.69,0.47,7.0,5.2,2.4,2.8,Transitioning
Cell_027,Lung,M2-skewed,0.18,0.79,6.6,8.9,1.1,5.0,Anti-inflammatory
Cell_028,Kidney,M1-skewed,0.82,0.19,7.6,1.2,5.3,1.4,Pro-inflammatory
Cell_029,Heart,M1-skewed,,0.13,7.6,1.1,6.1,1.1,Pro-inflammatory
Cell_030,Brain,Intermediate,0.68,0.43,7.1,5.0,2.3,2.2,Transitioning
Cell_031,Brain,Intermediate,0.39,0.65,7.0,5.3,3.6,3.2,Transitioning
Cell_032,Brain,Intermediate,0.69,0.64,7.9,3.2,3.7,4.5,Transitioning
Cell_033,Brain,M1-skewed,0.71,0.29,7.9,2.2,7.2,0.2,Pro-inflammatory
Cell_034,Liver,M2-skewed,0.12,0.92,6.4,7.4,1.6,4.9,Anti-inflammatory
Cell_035,Brain,M1-skewed,0.98,0.18,8.8,1.6,5.4,1.4,Pro-inflammatory
Cell_036,Lung,Intermediate,0.57,0.5,7.9,5.2,2.9,3.6,Transitioning
Cell_037,Brain,Intermediate,0.63,0.64,7.9,5.4,3.7,2.9,Transitioning
Cell_038,Heart,M1-skewed,0.99,0.29,8.7,1.7,7.0,0.5,Pro-inflammatory
Cell_039,Liver,Intermediate,0.66,0.5,8.2,5.1,3.9,4.3,Transitioning
Cell_040,Brain,M2-skewed,0.17,0.89,6.6,8.3,1.2,5.8,Anti-inflammatory
Cell_041,Heart,M1-skewed,0.78,0.16,9.0,2.2,6.3,1.2,Pro-inflammatory
Cell_042,Brain,M2-skewed,0.18,0.81,6.2,8.0,0.7,5.2,Anti-inflammatory
Cell_043,Liver,Intermediate,0.68,0.6,6.9,4.6,3.0,3.7,Transitioning
Cell_044,Heart,M1-skewed,0.86,0.12,8.3,1.7,7.9,0.1,Pro-inflammatory
Cell_045,Brain,Intermediate,0.38,0.68,6.7,5.6,2.7,2.3,Transitioning
Cell_046,Kidney,M2-skewed,0.06,0.98,6.6,7.4,0.9,5.4,Anti-inflammatory
Cell_047,Brain,M1-skewed,0.84,0.1,8.6,1.2,7.2,1.5,Pro-inflammatory
Cell_048,Kidney,Intermediate,0.47,0.6,7.2,4.2,3.5,4.4,Transitioning
Cell_049,Lung,M2-skewed,0.08,0.86,6.4,8.1,0.6,6.1,Anti-inflammatory
Cell_050,Lung,M1-skewed,0.78,0.02,8.3,1.5,7.0,0.8,Pro-inflammatory`
  }
};

function InteractiveTableViewer({ tables, isEn }) {
  const [selectedTableIdx, setSelectedTableIdx] = useState(0);
  const [searchQuery, setSearchQuery] = useState('');
  const [currentPage, setCurrentPage] = useState(1);
  const [pageSize, setPageSize] = useState(10);

  if (!tables || tables.length === 0) return null;

  const currentTable = tables[selectedTableIdx] || tables[0];
  const columns = currentTable.columns || [];
  const allRows = currentTable.rows || [];

  // Filter rows
  const filteredRows = allRows.filter(row => {
    if (!searchQuery.trim()) return true;
    const q = searchQuery.toLowerCase();
    return Object.values(row).some(val => String(val).toLowerCase().includes(q));
  });

  const totalPages = Math.max(1, Math.ceil(filteredRows.length / pageSize));
  const pageRows = filteredRows.slice((currentPage - 1) * pageSize, currentPage * pageSize);

  const handleExportCSV = () => {
    if (!columns.length || !allRows.length) return;
    const header = columns.join(',');
    const body = allRows.map(r => columns.map(c => `"${String(r[c] ?? '').replace(/"/g, '""')}"`).join(',')).join('\n');
    const blob = new Blob([`${header}\n${body}`], { type: 'text/csv;charset=utf-8;' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `${currentTable.name || 'sandbox_table'}.csv`;
    a.click();
    URL.revokeObjectURL(url);
  };

  return (
    <div className="space-y-3">
      {/* Controls & Table Switcher */}
      <div className="flex flex-wrap items-center justify-between gap-2 px-1">
        <div className="flex items-center gap-1.5 overflow-x-auto custom-scrollbar pb-1">
          {tables.map((tbl, idx) => (
            <button
              key={idx}
              onClick={() => { setSelectedTableIdx(idx); setCurrentPage(1); }}
              className={`px-3 py-1.5 rounded-lg text-xs font-mono font-bold transition-all flex items-center gap-1.5 ${
                selectedTableIdx === idx
                  ? 'bg-blue-600 text-white shadow-sm'
                  : 'bg-slate-800 text-slate-300 hover:bg-slate-700 border border-slate-700'
              }`}
            >
              <Table className="w-3.5 h-3.5" />
              <span>{tbl.name}</span>
              <span className="px-1.5 py-0.2 rounded bg-black/30 text-[10px] font-normal">
                {tbl.total_rows} × {tbl.total_cols}
              </span>
            </button>
          ))}
        </div>

        <div className="flex items-center gap-2">
          {/* Search bar */}
          <div className="relative">
            <SearchIcon className="w-3.5 h-3.5 text-slate-400 absolute left-2.5 top-2.5" />
            <input
              type="text"
              value={searchQuery}
              onChange={e => { setSearchQuery(e.target.value); setCurrentPage(1); }}
              placeholder={isEn ? "Filter rows..." : "Tìm kiếm dữ liệu..."}
              className="pl-8 pr-3 py-1 bg-slate-950 text-slate-200 text-xs rounded-lg border border-slate-700 focus:outline-none focus:border-blue-500 w-36 sm:w-44"
            />
          </div>

          {/* Export CSV button */}
          <button
            onClick={handleExportCSV}
            className="px-2.5 py-1 rounded-lg bg-emerald-600/20 hover:bg-emerald-600/30 text-emerald-400 border border-emerald-500/30 text-xs font-bold flex items-center gap-1 transition-colors"
            title="Export CSV"
          >
            <Download className="w-3.5 h-3.5" />
            <span className="hidden sm:inline">CSV</span>
          </button>
        </div>
      </div>

      {/* Table Container */}
      <div className="overflow-x-auto rounded-xl border border-slate-800 bg-slate-950/80 custom-scrollbar max-h-80">
        <table className="w-full text-left text-xs border-collapse font-sans">
          <thead>
            <tr className="bg-slate-900/90 border-b border-slate-800 text-slate-300 sticky top-0 z-10">
              <th className="py-2.5 px-3 font-mono text-[11px] text-slate-400 w-12 text-center border-r border-slate-800/60">
                #
              </th>
              {columns.map((col, cIdx) => (
                <th key={cIdx} className="py-2.5 px-3 font-mono font-semibold tracking-tight text-slate-200 whitespace-nowrap">
                  {col}
                </th>
              ))}
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-800/60 text-slate-300">
            {pageRows.length > 0 ? (
              pageRows.map((row, rIdx) => {
                const globalIndex = (currentPage - 1) * pageSize + rIdx + 1;
                return (
                  <tr key={rIdx} className="hover:bg-slate-800/50 transition-colors group">
                    <td className="py-2 px-3 font-mono text-[10px] text-slate-400 text-center border-r border-slate-800/40 bg-slate-900/30">
                      {globalIndex}
                    </td>
                    {columns.map((col, cIdx) => (
                      <td key={cIdx} className="py-2 px-3 font-mono text-[11px] whitespace-nowrap">
                        {row[col] !== undefined && row[col] !== null ? String(row[col]) : '-'}
                      </td>
                    ))}
                  </tr>
                );
              })
            ) : (
              <tr>
                <td colSpan={columns.length + 1} className="py-8 text-center text-slate-400 italic">
                  {isEn ? "No matching records found." : "Không tìm thấy dòng dữ liệu phù hợp."}
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>

      {/* Pagination Footer */}
      <div className="flex items-center justify-between text-xs text-slate-400 px-1 pt-1">
        <div className="text-[11px]">
          {isEn ? "Showing" : "Hiển thị"}{' '}
          <span className="font-bold text-slate-200">
            {filteredRows.length > 0 ? (currentPage - 1) * pageSize + 1 : 0}
          </span>{' '}
          -{' '}
          <span className="font-bold text-slate-200">
            {Math.min(currentPage * pageSize, filteredRows.length)}
          </span>{' '}
          / <span className="font-bold text-slate-200">{filteredRows.length}</span> {isEn ? "rows" : "dòng"}
        </div>

        <div className="flex items-center gap-2">
          <select
            value={pageSize}
            onChange={e => { setPageSize(Number(e.target.value)); setCurrentPage(1); }}
            className="bg-slate-900 border border-slate-700 text-slate-300 text-[11px] rounded px-1.5 py-0.5 focus:outline-none"
          >
            <option value={10}>10 / {isEn ? "page" : "trang"}</option>
            <option value={25}>25 / {isEn ? "page" : "trang"}</option>
            <option value={50}>50 / {isEn ? "page" : "trang"}</option>
          </select>

          <div className="flex items-center gap-1">
            <button
              onClick={() => setCurrentPage(p => Math.max(1, p - 1))}
              disabled={currentPage <= 1}
              className="px-2 py-0.5 rounded bg-slate-800 hover:bg-slate-700 disabled:opacity-40 text-slate-300 border border-slate-700 text-[11px]"
            >
              {isEn ? "Prev" : "Trước"}
            </button>
            <span className="text-[11px] font-mono text-slate-300 px-1">
              {currentPage}/{totalPages}
            </span>
            <button
              onClick={() => setCurrentPage(p => Math.min(totalPages, p + 1))}
              disabled={currentPage >= totalPages}
              className="px-2 py-0.5 rounded bg-slate-800 hover:bg-slate-700 disabled:opacity-40 text-slate-300 border border-slate-700 text-[11px]"
            >
              {isEn ? "Next" : "Sau"}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}

function StatisticalInsightsViewer({ insights, isEn }) {
  if (!insights || insights.length === 0) return null;

  return (
    <div className="space-y-3">
      <div className="text-xs text-slate-300 font-medium px-1 flex items-center justify-between">
        <span className="flex items-center gap-1.5">
          <Activity className="w-3.5 h-3.5 text-amber-400" />
          {isEn ? "Automated Statistical & Data Science Insights" : "Diễn giải Thống kê Định lượng Tự động"}
        </span>
        <span className="text-[10px] text-slate-400 font-mono">
          {insights.length} {isEn ? "metrics" : "chỉ số"}
        </span>
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-2.5">
        {insights.map((item, idx) => {
          const isCorr = item.category === 'correlation';
          const isDist = item.category === 'distribution';
          return (
            <div
              key={idx}
              className={`p-3 rounded-xl border backdrop-blur-sm transition-all ${
                isCorr 
                  ? 'bg-purple-950/20 border-purple-800/40 text-purple-200' 
                  : isDist 
                    ? 'bg-amber-950/20 border-amber-800/40 text-amber-200' 
                    : 'bg-slate-900/90 border-slate-800 text-slate-200'
              }`}
            >
              <div className="flex items-center justify-between mb-1">
                <span className="text-[11px] font-medium text-slate-400 truncate max-w-[170px]">
                  {item.metric}
                </span>
                <span className={`px-1.5 py-0.5 rounded text-[9px] font-bold uppercase tracking-wider ${
                  isCorr 
                    ? 'bg-purple-500/20 text-purple-300 border border-purple-500/30' 
                    : isDist 
                      ? 'bg-amber-500/20 text-amber-300 border border-amber-500/30' 
                      : 'bg-blue-500/20 text-blue-300 border border-blue-500/30'
                }`}>
                  {item.category}
                </span>
              </div>
              <div className="text-base font-bold font-mono text-white tracking-tight my-0.5">
                {item.value}
              </div>
              {item.subtext && (
                <div className="text-[10px] text-slate-400 truncate mt-1">
                  {item.subtext}
                </div>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
}

function InteractiveCodeSandboxBlock({ code, csvText, darkMode, isEn }) {
  const [isRunning, setIsRunning] = useState(false);
  const [result, setResult] = useState(null);
  const [isCopied, setIsCopied] = useState(false);
  const [activeTab, setActiveTab] = useState('code'); // 'code' | 'output' | 'figures' | 'tables' | 'insights'
  const [editableCode, setEditableCode] = useState(code);
  const [isEditing, setIsEditing] = useState(false);
  const [selectedFigure, setSelectedFigure] = useState(null);

  const handleRun = async () => {
    setIsRunning(true);
    try {
      const res = await safeFetch('/workspace/execute-code', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          code: editableCode,
          csv_text: csvText || '',
          timeout_seconds: 30.0,
        }),
      });
      const data = await res.json();
      setResult(data);

      // Smart tab selection based on outputs
      if (data.figures && data.figures.length > 0) {
        setActiveTab('figures');
      } else if (data.tables && data.tables.length > 0) {
        setActiveTab('tables');
      } else if (data.insights && data.insights.length > 0) {
        setActiveTab('insights');
      } else {
        setActiveTab('output');
      }
    } catch (err) {
      setResult({
        success: false,
        error: `Lỗi kết nối Sandbox: ${err.message}`,
        stdout: '',
        stderr: err.message,
        execution_time_ms: 0,
        figures: [],
        tables: [],
        insights: [],
      });
      setActiveTab('output');
    } finally {
      setIsRunning(false);
    }
  };

  const handleCopy = () => {
    navigator.clipboard.writeText(editableCode);
    setIsCopied(true);
    setTimeout(() => setIsCopied(false), 2000);
  };

  const handleDownload = () => {
    const blob = new Blob([editableCode], { type: 'text/plain' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = 'sandbox_eda.py';
    a.click();
    URL.revokeObjectURL(url);
  };

  return (
    <div className="rounded-2xl overflow-hidden my-4 border border-slate-700/80 bg-slate-900 shadow-xl backdrop-blur-md">
      {/* Header bar */}
      <div className="flex flex-wrap items-center justify-between gap-2 px-3.5 py-2.5 bg-slate-800/95 border-b border-slate-700/80 text-white">
        <div className="flex items-center gap-2">
          <div className="w-5 h-5 rounded-md bg-emerald-500/20 text-emerald-400 flex items-center justify-center font-bold text-[10px] border border-emerald-500/30">
            Py
          </div>
          <span className="text-xs font-mono font-bold text-slate-200">
            {isEn ? "Python Analytics Sandbox" : "Python Sandbox Phân Tích Dữ Liệu"}
          </span>
          {csvText ? (
            <span className="hidden sm:inline px-2 py-0.5 rounded-full bg-blue-500/20 text-blue-300 text-[10px] font-mono border border-blue-500/30">
              df loaded
            </span>
          ) : (
            <span className="hidden sm:inline px-2 py-0.5 rounded-full bg-slate-700 text-slate-400 text-[10px] font-mono">
              no dataset
            </span>
          )}
        </div>

        {/* Tab switchers & actions */}
        <div className="flex items-center gap-1.5">
          <div className="flex bg-slate-900/90 p-0.5 rounded-lg border border-slate-700 text-[11px] font-semibold">
            {result?.figures && result.figures.length > 0 && (
              <button
                onClick={() => setActiveTab('figures')}
                className={`px-2.5 py-1 rounded-md transition-colors flex items-center gap-1.5 ${activeTab === 'figures' ? 'bg-blue-600 text-white shadow-sm' : 'text-slate-400 hover:text-slate-200'}`}
              >
                <Image className="w-3 h-3 text-sky-400" />
                <span>Plots ({result.figures.length})</span>
              </button>
            )}

            {result?.tables && result.tables.length > 0 && (
              <button
                onClick={() => setActiveTab('tables')}
                className={`px-2.5 py-1 rounded-md transition-colors flex items-center gap-1.5 ${activeTab === 'tables' ? 'bg-blue-600 text-white shadow-sm' : 'text-slate-400 hover:text-slate-200'}`}
              >
                <Table className="w-3 h-3 text-emerald-400" />
                <span>Tables ({result.tables.length})</span>
              </button>
            )}

            {result?.insights && result.insights.length > 0 && (
              <button
                onClick={() => setActiveTab('insights')}
                className={`px-2.5 py-1 rounded-md transition-colors flex items-center gap-1.5 ${activeTab === 'insights' ? 'bg-blue-600 text-white shadow-sm' : 'text-slate-400 hover:text-slate-200'}`}
              >
                <Activity className="w-3 h-3 text-amber-400" />
                <span>Insights ({result.insights.length})</span>
              </button>
            )}

            <button
              onClick={() => setActiveTab('output')}
              className={`px-2.5 py-1 rounded-md transition-colors flex items-center gap-1.5 ${activeTab === 'output' ? 'bg-blue-600 text-white shadow-sm' : 'text-slate-400 hover:text-slate-200'}`}
            >
              <Terminal className="w-3 h-3" />
              <span>Console</span>
              {result && (
                <span className={`w-1.5 h-1.5 rounded-full ${result.success ? 'bg-emerald-400' : 'bg-rose-400'}`} />
              )}
            </button>

            <button
              onClick={() => setActiveTab('code')}
              className={`px-2.5 py-1 rounded-md transition-colors ${activeTab === 'code' ? 'bg-blue-600 text-white shadow-sm' : 'text-slate-400 hover:text-slate-200'}`}
            >
              {isEn ? 'Code' : 'Mã'}
            </button>
          </div>

          <button
            onClick={() => setIsEditing(!isEditing)}
            className={`p-1.5 rounded-lg border transition-colors ${isEditing ? 'bg-emerald-500/20 border-emerald-500/40 text-emerald-400' : 'hover:bg-slate-700 border-slate-700 text-slate-300'}`}
            title={isEditing ? (isEn ? "Done Editing" : "Xong") : (isEn ? "Edit Code" : "Sửa Code")}
          >
            {isEditing ? <Check className="w-3.5 h-3.5 text-emerald-400" /> : <Edit3 className="w-3.5 h-3.5" />}
          </button>

          <button
            onClick={handleCopy}
            className="p-1.5 rounded-lg hover:bg-slate-700 border border-slate-700 text-slate-300 transition-colors"
            title={isEn ? "Copy Code" : "Sao chép mã"}
          >
            {isCopied ? <Check className="w-3.5 h-3.5 text-emerald-400" /> : <Copy className="w-3.5 h-3.5" />}
          </button>

          <button
            onClick={handleDownload}
            className="p-1.5 rounded-lg hover:bg-slate-700 border border-slate-700 text-slate-300 transition-colors"
            title={isEn ? "Download .py" : "Tải file .py"}
          >
            <Download className="w-3.5 h-3.5" />
          </button>

          <button
            onClick={handleRun}
            disabled={isRunning}
            className="px-3 py-1 bg-gradient-to-r from-emerald-600 to-teal-600 hover:from-emerald-500 hover:to-teal-500 disabled:opacity-50 text-white rounded-lg text-xs font-bold transition-all shadow-md shadow-emerald-900/40 flex items-center gap-1.5 cursor-pointer ml-1 active:scale-95"
          >
            {isRunning ? (
              <>
                <Loader2 className="w-3.5 h-3.5 animate-spin" />
                <span>{isEn ? 'Running...' : 'Đang chạy...'}</span>
              </>
            ) : (
              <>
                <Play className="w-3.5 h-3.5 fill-white" />
                <span>{isEn ? 'Run in Sandbox' : 'Chạy Sandbox'}</span>
              </>
            )}
          </button>
        </div>
      </div>

      {/* Body content */}
      <div className="p-3">
        {activeTab === 'code' && (
          <div>
            {isEditing ? (
              <div className="relative">
                <textarea
                  value={editableCode}
                  onChange={(e) => setEditableCode(e.target.value)}
                  rows={8}
                  className="w-full bg-slate-950 text-emerald-400 font-mono text-xs p-3 rounded-xl border border-slate-700 focus:outline-none focus:border-emerald-500 custom-scrollbar resize-y"
                  placeholder="Nhập mã Python để chạy trong Sandbox..."
                />
                <button
                  onClick={() => setEditableCode(code)}
                  className="absolute right-3 top-3 text-[10px] text-slate-400 hover:text-white flex items-center gap-1 bg-slate-800 px-2 py-0.5 rounded border border-slate-700"
                >
                  <RotateCcw className="w-2.5 h-2.5" />
                  <span>Reset</span>
                </button>
              </div>
            ) : (
              <div className="max-h-72 overflow-y-auto custom-scrollbar rounded-xl bg-slate-950 p-3.5 border border-slate-800">
                <pre className="text-xs font-mono text-emerald-400 whitespace-pre-wrap">
                  {editableCode}
                </pre>
              </div>
            )}
          </div>
        )}

        {activeTab === 'output' && (
          <div className="space-y-2">
            <div className="flex items-center justify-between text-[11px] text-slate-400 px-1">
              <span className="font-mono flex items-center gap-1.5">
                <Terminal className="w-3.5 h-3.5 text-blue-400" />
                Console Standard Output
              </span>
              {result && (
                <span className="flex items-center gap-1 font-mono text-[10px] text-slate-400 bg-slate-800 px-2 py-0.5 rounded border border-slate-700">
                  <Clock className="w-3 h-3 text-slate-400" />
                  {result.execution_time_ms}ms
                </span>
              )}
            </div>

            <div className="max-h-72 overflow-y-auto custom-scrollbar rounded-xl bg-slate-950 p-3.5 border border-slate-800 text-xs font-mono">
              {!result ? (
                <div className="text-slate-400 italic flex items-center gap-2 py-2">
                  <span>Chưa chạy mã nguồn. Nhấn </span>
                  <span className="text-emerald-400 font-bold">"Chạy Sandbox"</span>
                  <span> để thực thi an toàn.</span>
                </div>
              ) : result.success ? (
                <div>
                  {result.stdout ? (
                    <pre className="text-slate-200 whitespace-pre-wrap">{result.stdout}</pre>
                  ) : (
                    <div className="text-slate-400 italic">Mã nguồn chạy thành công (Không có stdout).</div>
                  )}
                  {result.variables_summary && Object.keys(result.variables_summary).length > 0 && (
                    <div className="mt-3 pt-2.5 border-t border-slate-800">
                      <div className="text-[10px] uppercase tracking-wider text-slate-400 font-bold mb-1.5">
                        Biến số sinh ra:
                      </div>
                      <div className="grid grid-cols-1 sm:grid-cols-2 gap-1.5 text-[11px]">
                        {Object.entries(result.variables_summary).map(([k, v]) => (
                          <div key={k} className="bg-slate-900/90 px-2.5 py-1.5 rounded-lg border border-slate-800 flex justify-between items-center">
                            <span className="text-sky-400 font-mono font-semibold">{k}</span>
                            <span className="text-slate-300 truncate max-w-[150px] font-mono text-[10px]">{v}</span>
                          </div>
                        ))}
                      </div>
                    </div>
                  )}
                </div>
              ) : (
                <div className="text-rose-400 space-y-1.5">
                  <div className="font-bold flex items-center gap-1.5 text-rose-400">
                    <AlertCircle className="w-4 h-4" />
                    <span>Lỗi thực thi:</span>
                  </div>
                  <pre className="text-[11px] text-rose-300 whitespace-pre-wrap bg-rose-950/40 p-2 rounded border border-rose-900/50">{result.error || result.stderr}</pre>
                </div>
              )}
            </div>
          </div>
        )}

        {activeTab === 'figures' && result?.figures && (
          <div className="space-y-3">
            <div className="text-xs text-slate-300 font-medium px-1 flex items-center justify-between">
              <span className="flex items-center gap-1.5">
                <Image className="w-3.5 h-3.5 text-sky-400" />
                {isEn ? "Matplotlib & Seaborn High-Resolution Plots" : "Đồ thị Matplotlib / Seaborn sắc nét từ Sandbox"}
              </span>
              <span className="text-[10px] text-slate-400 font-mono">
                {result.figures.length} {isEn ? "figures" : "ảnh"}
              </span>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
              {result.figures.map((figBase64, figIdx) => (
                <div
                  key={figIdx}
                  className="rounded-xl overflow-hidden border border-slate-700 bg-white p-2.5 flex flex-col items-center group relative shadow-md"
                >
                  <img
                    src={figBase64}
                    alt={`Plot ${figIdx + 1}`}
                    className="w-full h-auto object-contain rounded-lg max-h-80 cursor-pointer hover:scale-[1.01] transition-transform"
                    onClick={() => setSelectedFigure(figBase64)}
                  />
                  <div className="w-full flex justify-between items-center mt-2 px-1 text-slate-600 text-[11px]">
                    <span className="font-bold font-mono">Figure {figIdx + 1}</span>
                    <div className="flex items-center gap-1.5">
                      <button
                        onClick={() => setSelectedFigure(figBase64)}
                        className="p-1 rounded-md bg-slate-100 hover:bg-slate-200 text-slate-700 transition-colors"
                        title={isEn ? "Expand Image" : "Phóng to"}
                      >
                        <Maximize2 className="w-3 h-3" />
                      </button>
                      <a
                        href={figBase64}
                        download={`matplotlib_plot_${figIdx + 1}.png`}
                        className="px-2.5 py-1 rounded-md bg-blue-50 hover:bg-blue-100 text-blue-700 text-[10px] font-bold flex items-center gap-1 transition-colors"
                      >
                        <Download className="w-3 h-3" />
                        <span>Lưu ảnh</span>
                      </a>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}

        {activeTab === 'tables' && result?.tables && (
          <InteractiveTableViewer tables={result.tables} isEn={isEn} />
        )}

        {activeTab === 'insights' && result?.insights && (
          <StatisticalInsightsViewer insights={result.insights} isEn={isEn} />
        )}
      </div>

      {/* Modal Zoom Figure */}
      {selectedFigure && (
        <div
          className="fixed inset-0 z-50 bg-black/80 backdrop-blur-sm flex items-center justify-center p-4"
          onClick={() => setSelectedFigure(null)}
        >
          <div className="relative max-w-5xl max-h-[92vh] bg-white p-4 rounded-2xl shadow-2xl" onClick={e => e.stopPropagation()}>
            <button
              onClick={() => setSelectedFigure(null)}
              className="absolute -top-3 -right-3 w-8 h-8 rounded-full bg-slate-900 text-white flex items-center justify-center font-bold shadow-lg cursor-pointer hover:bg-slate-800"
            >
              ✕
            </button>
            <img src={selectedFigure} alt="Enlarged Plot" className="max-w-full max-h-[82vh] object-contain rounded-xl" />
          </div>
        </div>
      )}
    </div>
  );
}

const markdownComponents = {
  h1: ({ node, ...props }) => (
    <h1 className="text-xl md:text-2xl font-black text-slate-900 dark:text-white mt-6 mb-3 pb-2 border-b border-slate-200 dark:border-slate-800 flex items-center gap-2" {...props} />
  ),
  h2: ({ node, ...props }) => (
    <div className="mt-8 mb-3 p-3 rounded-xl bg-gradient-to-r from-blue-100/80 via-blue-50/40 to-transparent dark:from-blue-950/50 dark:via-slate-900/30 dark:to-transparent border-l-4 border-blue-600 shadow-2xs">
      <h2 className="text-[17px] md:text-[18px] font-black text-slate-900 dark:text-white flex items-center gap-2 m-0" {...props} />
    </div>
  ),
  h3: ({ node, ...props }) => (
    <div className="mt-7 mb-3 p-3 rounded-xl bg-gradient-to-r from-blue-50/90 via-indigo-50/40 to-transparent dark:from-blue-950/40 dark:via-slate-900/40 dark:to-transparent border-l-4 border-blue-600 shadow-2xs">
      <h3 className="text-[15.5px] md:text-[16.5px] font-black text-slate-900 dark:text-white flex items-center gap-2 m-0" {...props} />
    </div>
  ),
  h4: ({ node, ...props }) => (
    <h4 className="text-[14px] md:text-[15px] font-bold text-blue-600 dark:text-sky-400 mt-4 mb-1.5 flex items-center gap-1.5" {...props} />
  ),
  p: ({ node, ...props }) => (
    <p className="text-[13.5px] leading-relaxed text-slate-700 dark:text-slate-300 my-2" {...props} />
  ),
  ul: ({ node, ...props }) => (
    <ul className="list-disc pl-5 my-2.5 space-y-1 text-[13.5px] text-slate-700 dark:text-slate-300 marker:text-blue-500" {...props} />
  ),
  ol: ({ node, ...props }) => (
    <ol className="list-decimal pl-5 my-2.5 space-y-1 text-[13.5px] text-slate-700 dark:text-slate-300 marker:font-bold marker:text-blue-500" {...props} />
  ),
  li: ({ node, ...props }) => (
    <li className="leading-relaxed pl-0.5" {...props} />
  ),
  blockquote: ({ node, ...props }) => (
    <blockquote className="my-3 pl-4 py-2.5 border-l-4 border-blue-500 bg-blue-50/70 dark:bg-blue-950/40 rounded-r-xl text-[13px] text-slate-700 dark:text-slate-300 font-medium" {...props} />
  ),
  table: ({ node, ...props }) => (
    <div className="my-4 overflow-x-auto rounded-xl border border-slate-200 dark:border-slate-800 shadow-2xs">
      <table className="min-w-full text-[12.5px] divide-y divide-slate-200 dark:divide-slate-800" {...props} />
    </div>
  ),
  thead: ({ node, ...props }) => (
    <thead className="bg-slate-100 dark:bg-slate-800/90 font-bold text-slate-800 dark:text-slate-200" {...props} />
  ),
  th: ({ node, ...props }) => (
    <th className="px-3.5 py-2.5 text-left font-bold text-[12px] tracking-wide text-slate-700 dark:text-slate-200 border-b border-slate-200 dark:border-slate-700" {...props} />
  ),
  td: ({ node, ...props }) => (
    <td className="px-3.5 py-2 text-slate-600 dark:text-slate-300 border-b border-slate-100 dark:border-slate-800/60" {...props} />
  ),
  hr: ({ node, ...props }) => (
    <hr className="my-6 border-slate-200 dark:border-slate-800" {...props} />
  ),
  strong: ({ node, ...props }) => (
    <strong className="font-bold text-slate-900 dark:text-white" {...props} />
  ),
};

export default function DataAnalysisPanel({ workspacePapers = [], darkMode, onSendToChat }) {
  const { t, language } = useLanguage();
  const isEn = language === 'en';

  const [messages, setMessages] = useState(() => [
    {
      sender: 'ai',
      text: isEn
        ? "Welcome to DataVoyager Analytics! Upload an Excel/CSV dataset to perform in-depth statistical synthesis, hypothesis testing, and exploratory data analysis (EDA)."
        : "Chào mừng bạn đến với DataVoyager Analytics! Tải lên tệp Excel/CSV để chạy phân tích thống kê định lượng, kiểm định giả thuyết và phân tích dữ liệu khám phá (EDA).",
      chart: null,
      kpis: null,
    }
  ]);
  const [input, setInput] = useState('');
  const [isTyping, setIsTyping] = useState(false);
  const [attachedFile, setAttachedFile] = useState(null);
  const [activeCsvText, setActiveCsvText] = useState('');
  const [datasetProfile, setDatasetProfile] = useState(null);
  const [copiedIndex, setCopiedIndex] = useState(null);
  const [showExampleQueries, setShowExampleQueries] = useState(true);
  
  // History State
  const [sessions, setSessions] = useState(() => {
    try {
      const saved = localStorage.getItem('workspace_eda_sessions');
      return saved ? JSON.parse(saved) : [];
    } catch {
      return [];
    }
  });
  const [activeSessionId, setActiveSessionId] = useState(null);
  const [isSidebarOpen, setIsSidebarOpen] = useState(false);

  React.useEffect(() => {
    if (messages.length <= 1) return;
    
    setSessions(prev => {
      let newSessions = [...prev];
      const existingIdx = newSessions.findIndex(s => s.id === activeSessionId);
      
      const sessionData = {
        id: activeSessionId || Date.now().toString(),
        timestamp: Date.now(),
        title: attachedFile?.name || datasetProfile?.filename || messages[1]?.text?.slice(0, 30) || 'Phân tích mới',
        messages: messages,
        profile: datasetProfile
      };

      if (existingIdx >= 0) {
        newSessions[existingIdx] = sessionData;
      } else {
        newSessions = [sessionData, ...newSessions];
        if (!activeSessionId) {
          setTimeout(() => setActiveSessionId(sessionData.id), 0);
        }
      }
      
      try {
        localStorage.setItem('workspace_eda_sessions', JSON.stringify(newSessions));
      } catch (err) {
        console.warn('LocalStorage limit exceeded, attempting to save fewer sessions...');
        try {
          // Keep only the most recent 2 sessions if quota is exceeded
          const limited = newSessions.slice(0, 2);
          localStorage.setItem('workspace_eda_sessions', JSON.stringify(limited));
        } catch(e2) {
          console.error('Failed to save session to localStorage:', e2);
        }
      }
      return newSessions;
    });
  }, [messages, datasetProfile, activeSessionId, attachedFile]);

  const handleNewSession = () => {
    setActiveSessionId(null);
    setDatasetProfile(null);
    setAttachedFile(null);
    setMessages([{
      sender: 'ai',
      text: isEn
        ? "Welcome to DataVoyager Analytics! Upload an Excel/CSV dataset to perform in-depth statistical synthesis, hypothesis testing, and exploratory data analysis (EDA)."
        : "Chào mừng bạn đến với DataVoyager Analytics! Tải lên tệp Excel/CSV để chạy phân tích thống kê định lượng, kiểm định giả thuyết và phân tích dữ liệu khám phá (EDA).",
      chart: null,
      kpis: null,
    }]);
    setIsSidebarOpen(false);
  };

  const loadSession = (session) => {
    setActiveSessionId(session.id);
    setMessages(session.messages || []);
    setDatasetProfile(session.profile || null);
    setAttachedFile(null);
    setIsSidebarOpen(false);
  };

  const handleDeleteSession = (sessionId, e) => {
    e.stopPropagation();
    setSessions(prev => {
      const updated = prev.filter(s => s.id !== sessionId);
      try {
        localStorage.setItem('workspace_eda_sessions', JSON.stringify(updated));
      } catch (err) {
        console.error('Failed to update localStorage after deleting session:', err);
      }
      return updated;
    });
    if (activeSessionId === sessionId) {
      handleNewSession();
    }
  };

  const handleClearAllSessions = () => {
    if (window.confirm(isEn ? 'Clear all analysis history?' : 'Bạn có chắc chắn muốn xóa toàn bộ lịch sử phân tích?')) {
      setSessions([]);
      localStorage.removeItem('workspace_eda_sessions');
      handleNewSession();
    }
  };

  const fileInputRef = useRef(null);
  const messagesEndRef = useRef(null);

  // ASTA 4-Category Example Queries Matrix
  const exampleQueryCategories = [
    {
      icon: <Sparkles className="w-4 h-4 text-emerald-500" />,
      title: isEn ? "Explore Tabula Sapiens & Biological Datasets" : "Khám phá Tập dữ liệu Y sinh & Tabula Sapiens",
      subtitle: isEn ? "Analyze cell types, compare across organs, and uncover biological insights." : "Phân tích loại tế bào, so sánh các cơ quan và trích xuất hiểu biết sinh học.",
      datasetKey: 'cell_biology',
      queries: [
        isEn 
          ? "Test whether kidney macrophages contain distinct subpopulations along the M1-M2 spectrum rather than being a homogeneous M2-skewed population." 
          : "Kiểm tra xem đại thực bào thận (kidney macrophages) có các phân nhóm riêng biệt dọc theo phổ M1-M2 hay là một quần thể thuần nhất thiên về M2.",
        isEn 
          ? "Compare M1 vs M2 expression scores across Kidney, Heart, and Lung tissues." 
          : "So sánh điểm biểu hiện M1 và M2 giữa các mô Thận (Kidney), Tim (Heart) và Phổi (Lung)."
      ]
    },
    {
      icon: <FolderOpen className="w-4 h-4 text-blue-500" />,
      title: isEn ? "Understand your Data & Seasonal Variations" : "Khám phá Dữ liệu Môi trường & Khí tượng",
      subtitle: isEn ? "Spot patterns, seasonal shifts, key variables, and data issues at a glance." : "Nhận diện quy luật, biến thiên theo mùa và các chất ô nhiễm nổi bật.",
      datasetKey: 'air_quality',
      queries: [
        isEn 
          ? "Investigate how air quality indicators (AQI, PM2.5, PM10, SO2, NO2) vary across different seasons and identify peak pollution periods." 
          : "Phân tích xu hướng chỉ số không khí (AQI, PM2.5, PM10, SO2, NO2) biến thiên theo 4 mùa và chỉ ra mùa nào ô nhiễm cao nhất.",
        isEn 
          ? "Calculate the ratio of PM2.5 to PM10 over time and plot the correlation with temperature." 
          : "Tính tỉ lệ đóng góp của PM2.5 / PM10 theo thời gian và vẽ biểu đồ tương quan với nhiệt độ."
      ]
    },
    {
      icon: <Microscope className="w-4 h-4 text-amber-500" />,
      title: isEn ? "Ask Scientific Questions & Test Hypotheses" : "Đặt câu hỏi Khoa học & Kiểm định Giả thuyết",
      subtitle: isEn ? "Compare groups, test hypotheses, and evaluate demographic or statistical differences." : "So sánh nhóm, kiểm định giả định và phân tích nhân tố tác động.",
      datasetKey: 'titanic',
      queries: [
        isEn 
          ? "What features differ most between survivors and non-survivors in the Titanic dataset? Analyze by Class, Sex and Age." 
          : "Những đặc trưng nào khác biệt rõ nhất giữa người sống sót và không sống sót? Phân tích theo Hạng vé, Giới tính và Độ tuổi.",
        isEn 
          ? "Who was most likely to survive the Titanic, and why? Please calculate percentages and visualize the results." 
          : "Nhóm hành khách nào có xác suất sống sót cao nhất và tại sao? Hãy tính tỉ lệ % và trực quan hóa kết quả."
      ]
    }
  ];

  const scrollToBottom = () => messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });



  const handleSelectDemoDataset = (key) => {
    if (DEMO_DATASETS[key]) {
      setAttachedFile({
        name: DEMO_DATASETS[key].name,
        content: DEMO_DATASETS[key].content
      });
      setActiveCsvText(DEMO_DATASETS[key].content);
    }
  };

  const handleFileChange = (e) => {
    const file = e.target.files?.[0];
    if (!file) return;
    const fileName = file.name.toLowerCase();

    // Support Excel binary files (.xlsx, .xls) by converting to clean CSV text
    if (fileName.endsWith('.xlsx') || fileName.endsWith('.xls')) {
      const reader = new FileReader();
      reader.onload = (ev) => {
        try {
          const data = new Uint8Array(ev.target.result);
          const workbook = XLSX.read(data, { type: 'array' });
          const firstSheetName = workbook.SheetNames[0];
          const worksheet = workbook.Sheets[firstSheetName];
          const csvText = XLSX.utils.sheet_to_csv(worksheet);
          setAttachedFile({ name: file.name, content: csvText });
          setActiveCsvText(csvText);
        } catch (err) {
          console.error('Error parsing Excel file in browser:', err);
          alert('Không thể đọc file Excel. Vui lòng kiểm tra lại định dạng.');
        }
      };
      reader.readAsArrayBuffer(file);
    } else {
      // Plain text CSV / TSV / JSON
      const reader = new FileReader();
      reader.onload = (ev) => {
        setAttachedFile({ name: file.name, content: ev.target.result });
        setActiveCsvText(ev.target.result);
      };
      reader.readAsText(file, 'utf-8');
    }
    e.target.value = null;
  };

  const handleSend = async (e, customText = null, customFile = null) => {
    if (e) e.preventDefault();
    const question = (customText || input).trim();
    if (!question) return;

    const fileToUse = customFile || attachedFile;
    if (fileToUse?.content) {
      setActiveCsvText(fileToUse.content);
    }
    const userMsg = { 
      sender: 'user', 
      text: question, 
      attachment: fileToUse ? fileToUse.name : null 
    };
    
    setMessages((prev) => [...prev, userMsg]);
    if (!customText) setInput('');
    
    const fileSnapshot = fileToUse;
    setAttachedFile(null);
    setIsTyping(true);
    setTimeout(scrollToBottom, 50);

    try {
      const res = await safeFetch('/workspace/analyze-data', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ 
          question, 
          csv_text: fileSnapshot?.content ?? '', 
          filename: fileSnapshot?.name ?? '' 
        }),
      });

      if (!res.ok) {
        const errData = await res.json().catch(() => ({}));
        throw new Error(errData.detail || `Lỗi máy chủ (${res.status})`);
      }
      
      const data = await res.json();

      if (data.dataset_profile) {
        setDatasetProfile(data.dataset_profile);
      }

      setMessages((prev) => [
        ...prev, 
        { 
          sender: 'ai', 
          text: data.answer ?? data.detail ?? 'Hoàn tất phân tích dữ liệu.',
          charts: data.charts ?? (data.chart ? [data.chart] : null),
          kpis: data.kpis ?? null,
          profile: data.dataset_profile ?? null,
          python_code: data.python_code ?? null,
          figures: data.figures ?? null,
          block_outputs: data.block_outputs ?? null,
        }
      ]);
    } catch (err) {
      setMessages((prev) => [
        ...prev, 
        { 
          sender: 'ai', 
          text: `❌ Lỗi khi phân tích dữ liệu: ${err.message}. Vui lòng thử lại.` 
        }
      ]);
    } finally {
      setIsTyping(false);
      setTimeout(scrollToBottom, 50);
    }
  };

  const handleAutoEDA = () => {
    if (!attachedFile) return;
    const promptText = isEn
      ? "Perform a rigorous 7-section Exploratory Data Analysis (EDA) on this dataset according to standard data science methodology: 1. Data structure overview, 2. Data quality and missingness audit (per-column drop/impute analysis), 3. Univariate distributions and IQR outlier tests, 4. Time-series continuity and seasonality/DST integrity, 5. Multivariate correlations with Pearson p-values, 6. Target variable and forecast evaluation, 7. Preprocessing action plan and recommendations. Verify all figures quantitatively with Python code."
      : "Hãy thực hiện phân tích khám phá dữ liệu (EDA) chuẩn mực theo đúng khung EDA 7 phần chuyên sâu: 1. Tổng quan cấu trúc dữ liệu, 2. Kiểm toán chất lượng dữ liệu và tỷ lệ khuyết từng cột (phân nhóm cột rỗng 100% / hằng số cần drop vs khuyết thấp cần interpolate), 3. Phân phối đơn biến và kiểm định ngoại lai IQR, 4. Phân tích chuỗi thời gian và kiểm tra múi giờ/DST, 5. Quan hệ đa biến và ma trận tương quan Pearson kèm p-value, 6. Phân tích biến mục tiêu và sai số dự báo, 7. Kết luận và kế hoạch tiền xử lý dữ liệu. Mọi số liệu phải được tính toán chính xác bằng mã Python thực thi.";
    
    handleSend(null, promptText, attachedFile);
  };

  const handleCopy = (text, idx) => {
    navigator.clipboard.writeText(text);
    setCopiedIndex(idx);
    setTimeout(() => setCopiedIndex(null), 2000);
  };

  const dm = darkMode;

  return (
    <div className="flex-1 min-h-0 flex relative bg-transparent overflow-hidden">
      
      {/* Sidebar Backdrop Overlay */}
      {isSidebarOpen && (
        <div 
          className="absolute inset-0 bg-slate-900/20 backdrop-blur-sm z-40 transition-opacity"
          onClick={() => setIsSidebarOpen(false)}
        />
      )}

      {/* History Sidebar */}
      <div className={`absolute top-0 left-0 h-full w-72 bg-white dark:bg-slate-900 border-r border-slate-200 dark:border-slate-800 z-50 transform transition-transform duration-300 shadow-xl flex flex-col ${
        isSidebarOpen ? 'translate-x-0' : '-translate-x-full'
      }`}>
        <div className="p-4 border-b border-slate-200 dark:border-slate-800 flex items-center justify-between">
          <div className="flex items-center gap-2">
            <Layers className="w-4 h-4 text-blue-500" />
            <h3 className="font-bold text-sm text-slate-800 dark:text-slate-200">
              {isEn ? 'Analysis History' : 'Lịch sử phân tích'}
            </h3>
          </div>
          <button 
            onClick={() => setIsSidebarOpen(false)}
            className="p-1 rounded-md hover:bg-slate-100 dark:hover:bg-slate-800 text-slate-500 transition-colors cursor-pointer"
          >
            <X className="w-4 h-4" />
          </button>
        </div>
        
        <div className="p-3 border-b border-slate-200 dark:border-slate-800 shrink-0">
          <button
            onClick={handleNewSession}
            className="w-full py-2 bg-blue-50 hover:bg-blue-100 dark:bg-blue-900/30 dark:hover:bg-blue-900/50 text-blue-600 dark:text-blue-400 rounded-lg text-xs font-bold transition-colors flex items-center justify-center gap-2 cursor-pointer"
          >
            <Sparkles className="w-3.5 h-3.5" />
            <span>{isEn ? 'New Analysis' : 'Phiên phân tích mới'}</span>
          </button>
        </div>

        <div className="flex-1 overflow-y-auto p-2 space-y-1 custom-scrollbar">
          {sessions.length === 0 ? (
            <div className="text-center p-4 text-xs text-slate-500">
              {isEn ? 'No history yet.' : 'Chưa có lịch sử phân tích.'}
            </div>
          ) : (
            sessions.map(s => (
              <div
                key={s.id}
                onClick={() => loadSession(s)}
                className={`group w-full text-left p-2.5 rounded-xl transition-all flex items-center justify-between gap-2 cursor-pointer ${
                  activeSessionId === s.id 
                    ? 'bg-blue-50 dark:bg-blue-900/30 border-blue-200 dark:border-blue-800/60 border shadow-xs' 
                    : 'hover:bg-slate-100/70 dark:hover:bg-slate-800/50 border border-transparent'
                }`}
              >
                <div className="flex-1 min-w-0">
                  <div className={`text-xs font-semibold truncate ${activeSessionId === s.id ? 'text-blue-700 dark:text-blue-300' : 'text-slate-700 dark:text-slate-300'}`}>
                    {s.title}
                  </div>
                  <div className="text-[10px] text-slate-400 mt-0.5">
                    {new Date(s.timestamp).toLocaleString(isEn ? 'en-US' : 'vi-VN')}
                  </div>
                </div>
                <button
                  onClick={(e) => handleDeleteSession(s.id, e)}
                  title={isEn ? "Delete this session" : "Xóa phiên này"}
                  className="p-1.5 rounded-lg text-slate-400 hover:text-red-500 hover:bg-red-50 dark:hover:bg-red-950/40 opacity-0 group-hover:opacity-100 transition-all shrink-0 cursor-pointer"
                >
                  <Trash2 className="w-3.5 h-3.5" />
                </button>
              </div>
            ))
          )}
        </div>

        {sessions.length > 0 && (
          <div className="p-3 border-t border-slate-200 dark:border-slate-800 shrink-0">
            <button
              onClick={handleClearAllSessions}
              className="w-full py-1.5 px-2.5 text-slate-500 hover:text-red-600 hover:bg-red-50 dark:hover:bg-red-950/30 rounded-lg text-[11px] font-medium transition-colors flex items-center justify-center gap-1.5 cursor-pointer"
            >
              <Trash2 className="w-3.5 h-3.5" />
              <span>{isEn ? 'Clear all history' : 'Xóa toàn bộ lịch sử'}</span>
            </button>
          </div>
        )}
      </div>

      {/* Main Content Area */}
      <div className="flex-1 flex flex-col relative w-full h-full">

      {/* Toggle Sidebar Button */}
      <button
        onClick={() => setIsSidebarOpen(true)}
        className={`absolute top-4 left-4 z-40 p-2 rounded-xl border bg-white dark:bg-slate-800 text-slate-600 dark:text-slate-300 hover:bg-slate-50 dark:hover:bg-slate-700 shadow-sm transition-all cursor-pointer ${isSidebarOpen ? 'opacity-0 pointer-events-none' : 'opacity-100'}`}
        title={isEn ? "History" : "Lịch sử"}
      >
        <FolderOpen className="w-4 h-4" />
      </button>

      {/* Main Conversation & Analysis Feed */}
      <div className="flex-1 overflow-y-auto custom-scrollbar">
        <div className="w-full max-w-4xl mx-auto space-y-6 py-6 px-4 md:px-8">
          
          {/* Active Dataset Profile Health Card */}
          {datasetProfile && (
            <DatasetHealthCard 
              profile={datasetProfile} 
              filename={attachedFile?.name || 'Tập dữ liệu đã phân tích'} 
              darkMode={dm}
              onRunAutoEDA={handleAutoEDA}
            />
          )}

          {messages.map((msg, idx) => (
            <div key={idx} className={`flex gap-3.5 ${msg.sender === 'user' ? 'justify-end' : 'justify-start'}`}>
              {msg.sender === 'ai' && (
                <div className="w-9 h-9 rounded-xl bg-gradient-to-tr from-blue-600 to-indigo-600 text-white flex items-center justify-center shrink-0 shadow-md">
                  <BarChart2 className="w-4 h-4" />
                </div>
              )}

              <div className={`text-[14px] leading-relaxed ${
                msg.sender === 'user'
                  ? 'px-5 py-3.5 rounded-3xl rounded-tr-sm max-w-[85%] md:max-w-[75%] bg-blue-600 text-white font-medium shadow-sm'
                  : 'py-1.5 w-full max-w-full text-slate-800 dark:py-1.5 dark:w-full dark:max-w-full dark:text-slate-200'
              }`}>
                
                {/* User Attachment Chip */}
                {msg.attachment && (
                  <div className="mb-2 inline-flex items-center gap-1.5 px-2.5 py-1 rounded-lg bg-blue-100 dark:bg-blue-900/30 text-blue-700 dark:text-blue-300 text-[11px] font-semibold border border-blue-200 dark:border-blue-800/50">
                    <Paperclip className="w-3 h-3" />
                    <span>{msg.attachment}</span>
                  </div>
                )}

                <div className={msg.sender === 'user' ? 'whitespace-pre-wrap mb-3' : 'max-w-none text-slate-800 dark:text-slate-200 mb-3'}>
                  {msg.sender === 'user' ? msg.text : (
                    (!msg.block_outputs || msg.block_outputs.length === 0) ? (
                      <ReactMarkdown 
                        remarkPlugins={[remarkMath, remarkGfm]}
                        rehypePlugins={[rehypeKatex]}
                        components={markdownComponents}
                      >
                        {formatMathAndMarkdown(msg.text)}
                      </ReactMarkdown>
                    ) : (
                      msg.text.split(/```(?:python|py)\s*[\r\n]+([\s\S]*?)```/i).map((part, index) => {
                        if (index % 2 === 0) {
                          if (!part.trim()) return null;
                          return (
                            <ReactMarkdown 
                              key={index}
                              remarkPlugins={[remarkMath, remarkGfm]}
                              rehypePlugins={[rehypeKatex]}
                              components={markdownComponents}
                            >
                              {formatMathAndMarkdown(part)}
                            </ReactMarkdown>
                          );
                        } else {
                          const blockIndex = Math.floor(index / 2);
                          const output = msg.block_outputs[blockIndex];
                          return (
                            <div key={index} className="my-4">
                              <div className="rounded-lg bg-slate-900 border border-slate-800 overflow-hidden shadow-sm">
                                <div className="px-3 py-1.5 bg-slate-800/80 border-b border-slate-800 text-[11px] font-mono text-slate-400 flex items-center gap-1.5">
                                  <FileCode className="w-3.5 h-3.5" /> Python
                                </div>
                                <pre className="p-4 text-[13px] font-mono text-slate-300 overflow-x-auto whitespace-pre-wrap">
                                  {part}
                                </pre>
                              </div>
                              
                              {output && (output.stdout || (output.figures && output.figures.length > 0)) && (
                                <div className="mt-2 pl-2 border-l-4 border-blue-500/30">
                                  {output.stdout && (
                                    <pre className="p-3 text-[12px] font-mono text-slate-600 dark:text-slate-400 bg-slate-50 dark:bg-slate-900/50 rounded-lg whitespace-pre-wrap mb-3 border border-slate-100 dark:border-slate-800">
                                      {output.stdout}
                                    </pre>
                                  )}
                                  {output.figures && output.figures.length > 0 && (
                                    <div className="flex flex-col gap-4">
                                      {output.figures.map((fig, fIdx) => (
                                        <div key={fIdx} className="bg-white dark:bg-slate-900 p-2 rounded-xl border border-slate-200 dark:border-slate-800 shadow-sm inline-block">
                                          <img 
                                            src={fig} 
                                            alt={`Figure ${blockIndex}-${fIdx}`} 
                                            className="max-w-full h-auto rounded-lg cursor-pointer hover:opacity-95 transition-opacity"
                                            onClick={() => setSelectedZoomFigure(fig)}
                                          />
                                        </div>
                                      ))}
                                    </div>
                                  )}
                                </div>
                              )}
                            </div>
                          );
                        }
                      })
                    )
                  )}
                </div>

                {/* KPI Metrics Cards */}
                {msg.kpis && msg.kpis.length > 0 && (
                  <KPICardsGrid kpis={msg.kpis} darkMode={dm} />
                )}

                {/* Interactive Visual Charts (Recharts) */}
                {msg.charts && msg.charts.length > 0 && (
                  <div className="grid grid-cols-1 xl:grid-cols-2 gap-4 mt-4">
                    {msg.charts.map((chartItem, cIdx) => (
                      <DynamicDataChart key={cIdx} chart={chartItem} darkMode={dm} />
                    ))}
                  </div>
                )}

                {/* Scientific Figures & Plots (Matplotlib) - Fallback for non-interleaved */}
                {msg.figures && msg.figures.length > 0 && (!msg.block_outputs || msg.block_outputs.length === 0) && (
                  <div className="my-5 p-4 rounded-2xl border bg-slate-900/90 dark:bg-slate-900/90 border-slate-700/80 shadow-xl">
                    <div className="flex items-center justify-between gap-2 mb-3 pb-2 border-b border-slate-700/80 text-white">
                      <div className="flex items-center gap-2">
                        <Image className="w-4 h-4 text-sky-400" />
                        <h4 className="font-bold text-xs text-slate-100">
                          {isEn ? "Scientific Data Visualizations & Plots" : "Đồ thị Trực quan hóa Dữ liệu Thực nghiệm (EDA Figures)"}
                        </h4>
                      </div>
                      <span className="text-[10px] font-bold px-2 py-0.5 rounded-full bg-sky-500/20 text-sky-300 border border-sky-500/30">
                        {msg.figures.length} {isEn ? "figures" : "đồ thị trực quan"}
                      </span>
                    </div>

                    <div className="grid grid-cols-1 md:grid-cols-2 gap-3.5">
                      {msg.figures.map((figBase64, fIdx) => (
                        <div key={fIdx} className="rounded-xl overflow-hidden border border-slate-800 bg-slate-950 p-2.5 group relative flex flex-col shadow-md">
                          <div 
                            className="relative overflow-hidden rounded-lg cursor-pointer bg-white flex items-center justify-center min-h-[220px]" 
                            onClick={() => setSelectedZoomFigure(figBase64)}
                          >
                            <img 
                              src={figBase64} 
                              alt={`Figure ${fIdx + 1}`} 
                              className="w-full h-auto object-contain max-h-[300px] group-hover:scale-[1.02] transition-transform duration-200" 
                            />
                            <div className="absolute inset-0 bg-black/20 opacity-0 group-hover:opacity-100 transition-opacity flex items-center justify-center pointer-events-none">
                              <span className="px-3 py-1.5 rounded-lg bg-black/75 text-white text-xs font-bold flex items-center gap-1.5 shadow-lg backdrop-blur-xs">
                                <Maximize2 className="w-3.5 h-3.5" />
                                {isEn ? "Click to enlarge" : "Phóng to"}
                              </span>
                            </div>
                          </div>
                          <div className="mt-2 pt-2 border-t border-slate-800 flex items-center justify-between text-[11px] text-slate-400">
                            <span className="font-mono font-semibold">Đồ thị #{fIdx + 1}</span>
                          </div>
                        </div>
                      ))}
                    </div>
                  </div>
                )}

                {/* Technical Appendix: Python EDA Sandbox & Notebook Export (At the very end) */}
                {msg.python_code && (
                  <div className="mt-5 pt-3 border-t border-slate-200 dark:border-slate-800/80">
                    <div className="text-xs font-bold text-slate-700 dark:text-slate-300 mb-2 flex items-center gap-1.5">
                      <FileCode className="w-4 h-4 text-emerald-500" />
                      <span>{isEn ? "Technical Appendix: Executable Python Script & Notebook Export" : "Phụ lục Kỹ thuật: Mã nguồn tổng hợp EDA & Công cụ Sandbox"}</span>
                    </div>
                    <InteractiveCodeSandboxBlock 
                      code={msg.python_code} 
                      csvText={activeCsvText} 
                      darkMode={dm} 
                      isEn={isEn} 
                    />
                  </div>
                )}

                {/* Standalone HTML Report & Executive Export Toolbar */}
                {msg.sender === 'ai' && (
                  <div className="flex flex-wrap items-center justify-between gap-2.5 mt-5 p-3.5 bg-gradient-to-r from-blue-50/80 to-indigo-50/40 dark:from-slate-900/90 dark:to-blue-950/40 border border-blue-100 dark:border-blue-900/40 rounded-xl shadow-xs">
                    <div className="flex items-center gap-2 text-xs font-bold text-blue-700 dark:text-blue-300">
                      <Globe className="w-4 h-4 text-blue-500" />
                      <span>{isEn ? "Executive Report & Export Tools" : "Xuất Báo Cáo & Xem Toàn Màn Hình"}</span>
                    </div>
                    
                    <div className="flex flex-wrap items-center gap-2">
                      <button
                        onClick={() => {
                          const html = generateStandaloneHTMLReport({
                            message: msg,
                            filename: attachedFile?.name || 'dataset.csv',
                            title: isEn ? 'Exploratory Data Analysis (EDA) Report' : 'Báo Cáo Phân Tích Khám Phá Dữ Liệu (EDA)'
                          });
                          openReportInNewTab(html);
                        }}
                        className="px-3 py-1.5 rounded-lg bg-blue-600 hover:bg-blue-700 active:scale-98 text-white text-xs font-semibold flex items-center gap-1.5 shadow-sm transition-all cursor-pointer"
                        title={isEn ? "Open full standalone HTML report in a new tab" : "Mở toàn văn báo cáo trong tab trình duyệt mới"}
                      >
                        <ExternalLink className="w-3.5 h-3.5" />
                        <span>{isEn ? "Open HTML (New Tab)" : "Mở bản HTML (Tab mới)"}</span>
                      </button>

                      <button
                        onClick={() => {
                          const html = generateStandaloneHTMLReport({
                            message: msg,
                            filename: attachedFile?.name || 'dataset.csv',
                            title: isEn ? 'Exploratory Data Analysis (EDA) Report' : 'Báo Cáo Phân Tích Khám Phá Dữ Liệu (EDA)'
                          });
                          downloadHTMLReport(html, `Bao_cao_EDA_${attachedFile?.name ? attachedFile.name.replace(/\.[^/.]+$/, '') : 'dataset'}.html`);
                        }}
                        className="px-3 py-1.5 rounded-lg bg-white dark:bg-slate-800 hover:bg-slate-50 dark:hover:bg-slate-700 active:scale-98 text-slate-700 dark:text-slate-200 border border-slate-200 dark:border-slate-700 text-xs font-semibold flex items-center gap-1.5 shadow-xs transition-all cursor-pointer"
                        title="Tải file HTML độc lập về máy"
                      >
                        <Download className="w-3.5 h-3.5 text-blue-500" />
                        <span>{isEn ? "Download HTML" : "Tải HTML"}</span>
                      </button>

                      <button
                        onClick={() => {
                          downloadJupyterNotebook(msg, `eda_notebook_${attachedFile?.name ? attachedFile.name.replace(/\.[^/.]+$/, '') : 'dataset'}.ipynb`);
                        }}
                        className="px-3 py-1.5 rounded-lg bg-white dark:bg-slate-800 hover:bg-slate-50 dark:hover:bg-slate-700 active:scale-98 text-slate-700 dark:text-slate-200 border border-slate-200 dark:border-slate-700 text-xs font-semibold flex items-center gap-1.5 shadow-xs transition-all cursor-pointer"
                        title="Tải file Jupyter Notebook (.ipynb) để mở trên Google Colab / VS Code"
                      >
                        <BookOpen className="w-3.5 h-3.5 text-amber-500" />
                        <span>{isEn ? "Download .ipynb" : "Tải .ipynb"}</span>
                      </button>

                      <button
                        onClick={() => handleCopy(msg.text, idx)}
                        className="px-2.5 py-1.5 rounded-lg bg-white dark:bg-slate-800 hover:bg-slate-50 dark:hover:bg-slate-700 active:scale-98 text-slate-600 dark:text-slate-300 border border-slate-200 dark:border-slate-700 text-xs font-semibold flex items-center gap-1 shadow-xs transition-all cursor-pointer"
                        title="Sao chép nội dung văn bản"
                      >
                        {copiedIndex === idx ? <Check className="w-3.5 h-3.5 text-emerald-500" /> : <Copy className="w-3.5 h-3.5" />}
                        <span>{copiedIndex === idx ? (isEn ? 'Copied' : 'Đã chép') : (isEn ? 'Copy' : 'Sao chép')}</span>
                      </button>
                    </div>
                  </div>
                )}
              </div>
            </div>
          ))}

          {/* Typing Indicator */}
          {isTyping && (
            <div className="flex gap-3.5 justify-start">
              <div className="w-9 h-9 rounded-xl bg-blue-600 text-white flex items-center justify-center shrink-0 shadow-md">
                <BarChart2 className="w-4 h-4" />
              </div>
              <div className={`py-2 px-4 rounded-2xl flex items-center gap-2 ${'bg-slate-100 text-slate-700 dark:bg-slate-900 dark:text-slate-300'}`}>
                <RefreshCw className="w-3.5 h-3.5 animate-spin text-blue-500" />
                <span className="text-xs font-semibold">DataVoyager đang tính toán thống kê & phân tích dữ liệu...</span>
              </div>
            </div>
          )}


          {/* Scientific Query Library Hub */}
          {messages.length === 1 && (
            <div className="pt-2 space-y-3">
              <div className="flex items-center justify-between border-b pb-2 dark:border-slate-800 border-slate-200">
                <div className="flex items-center gap-2">
                  <Sparkles className="w-4 h-4 text-emerald-500" />
                  <span className="text-xs font-extrabold uppercase tracking-wider text-slate-600 dark:text-slate-300">
                    {isEn ? 'Scientific Query & Dataset Library' : 'Thư viện Câu hỏi & Dữ liệu Phân tích Mẫu'}
                  </span>
                </div>

                <button
                  onClick={() => setShowExampleQueries(!showExampleQueries)}
                  className="text-xs font-semibold text-blue-600 dark:text-blue-400 hover:underline flex items-center gap-1 cursor-pointer"
                >
                  <span>{showExampleQueries ? (isEn ? 'Hide example queries' : 'Ẩn câu hỏi mẫu') : (isEn ? 'Show example queries' : 'Hiện câu hỏi mẫu')}</span>
                  {showExampleQueries ? <ChevronUp className="w-3.5 h-3.5" /> : <ChevronDown className="w-3.5 h-3.5" />}
                </button>
              </div>

              {showExampleQueries && (
                <div className="space-y-3 animate-in fade-in duration-200">
                  {exampleQueryCategories.map((cat, catIdx) => (
                    <div 
                      key={catIdx}
                      className={`p-4 rounded-2xl border transition-all ${
                        'bg-white border-slate-200/90 shadow-2xs hover:border-slate-300 dark:bg-slate-900/60 dark:border-slate-800/80 dark:hover:border-slate-700'
                      }`}
                    >
                      <div className="flex items-start gap-2.5 mb-2.5">
                        <div className="p-1.5 rounded-lg bg-slate-100 dark:bg-slate-800 shrink-0 mt-0.5">
                          {cat.icon}
                        </div>
                        <div>
                          <h4 className="font-bold text-xs text-slate-800 dark:text-slate-100 flex items-center gap-2">
                            <span>{cat.title}</span>
                          </h4>
                          <p className="text-[11px] text-slate-500 dark:text-slate-400 mt-0.5">
                            {cat.subtitle}
                          </p>
                        </div>
                      </div>

                      <div className="space-y-1.5 pl-8">
                        {cat.queries.map((q, qIdx) => (
                          <button
                            key={qIdx}
                            onClick={() => {
                              handleSelectDemoDataset(cat.datasetKey);
                              const fileObj = (DEMO_DATASETS[cat.datasetKey] ? { name: DEMO_DATASETS[cat.datasetKey].name, content: DEMO_DATASETS[cat.datasetKey].content } : null);
                              handleSend(null, q, fileObj);
                            }}
                            className="w-full text-left py-1.5 px-2.5 rounded-lg text-xs transition-colors flex items-start justify-between group text-slate-600 dark:text-slate-300 hover:bg-blue-50 dark:hover:bg-blue-950/40 hover:text-blue-600 dark:hover:text-blue-400 cursor-pointer"
                          >
                            <span className="leading-relaxed pr-2">· {q}</span>
                            <ArrowRight className="w-3.5 h-3.5 text-slate-300 group-hover:text-blue-500 group-hover:translate-x-0.5 transition-all shrink-0 mt-0.5" />
                          </button>
                        ))}
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          )}

          <div ref={messagesEndRef} />
        </div>
      </div>

      {/* Input Form & ASTA-Style Dataset Attachment Pill */}
      <div className="relative mt-2 shrink-0 w-full flex flex-col items-center gap-2 mb-4 px-4">
        
        {/* ASTA Style Attachment Chip */}
        {attachedFile && (
          <div className="self-start flex items-center gap-2 px-3 py-1.5 rounded-xl border text-[12px] font-semibold shadow-xs animate-in fade-in duration-150 bg-slate-50 border-slate-200 text-slate-700 dark:bg-slate-800 dark:border-slate-700 dark:text-slate-200">
            {attachedFile.name.toLowerCase().endsWith('.csv') ? (
              <span className="px-1.5 py-0.5 rounded bg-sky-100 text-sky-700 dark:bg-sky-900/50 dark:text-sky-300 text-[10px] font-bold">CSV</span>
            ) : attachedFile.name.toLowerCase().endsWith('.tsv') ? (
              <span className="px-1.5 py-0.5 rounded bg-violet-100 text-violet-700 dark:bg-violet-900/50 dark:text-violet-300 text-[10px] font-bold">TSV</span>
            ) : (
              <FileSpreadsheet className="w-3.5 h-3.5 text-emerald-500" />
            )}
            <span className="max-w-[260px] truncate">{attachedFile.name}</span>
            <button 
              onClick={() => setAttachedFile(null)} 
              className="ml-1 text-slate-400 hover:text-red-500 transition-colors cursor-pointer"
              title="Gỡ bỏ tập dữ liệu"
            >
              <X className="w-3.5 h-3.5" />
            </button>
          </div>
        )}

        <form onSubmit={handleSend} className="relative w-full max-w-4xl mx-auto">
          <input 
            ref={fileInputRef} 
            type="file" 
            accept=".csv,.tsv,.txt,.json,.xlsx,.xls" 
            className="hidden" 
            onChange={handleFileChange} 
          />

          <button
            type="button"
            onClick={() => fileInputRef.current?.click()}
            title="Đính kèm tập dữ liệu (Hỗ trợ CSV, Excel .xlsx, .xls, TSV, TXT)"
            className={`absolute left-3 top-1/2 -translate-y-1/2 p-2 rounded-xl transition-colors cursor-pointer ${
              attachedFile ? 'text-blue-500 bg-blue-50 dark:bg-blue-950/40' : 'text-slate-400 hover:text-slate-600 hover:bg-slate-100 dark:text-slate-400 dark:hover:text-slate-200 dark:hover:bg-slate-700'
            }`}
          >
            <Paperclip className="w-4 h-4" />
          </button>

          <input
            type="text"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            placeholder={isEn ? "Ask a scientific question, test hypothesis, analyze trends, or request charts..." : "Đặt câu hỏi khoa học, phân tích xu hướng, kiểm định giả thuyết hoặc yêu cầu vẽ biểu đồ..."}
            className={`w-full pl-12 pr-32 py-3.5 border rounded-2xl text-[13.5px] font-medium focus:outline-none focus:border-blue-500 focus:ring-4 focus:ring-blue-500/10 shadow-sm transition-all ${
              'bg-white border-slate-200 text-slate-900 placeholder-slate-400 dark:bg-slate-900 dark:border-slate-700 dark:text-white dark:placeholder-slate-500'
            }`}
          />

          <button
            type="submit"
            disabled={!input.trim() && !attachedFile}
            className="absolute right-2 top-1/2 -translate-y-1/2 bg-blue-600 hover:bg-blue-700 disabled:opacity-40 disabled:cursor-not-allowed text-white px-4 py-2 rounded-xl text-xs font-bold transition-transform active:scale-95 flex items-center gap-1.5 shadow-md cursor-pointer"
          >
            <span>{isEn ? 'Analyze' : 'Phân tích'}</span>
            <Send className="w-3.5 h-3.5" />
          </button>
        </form>
      </div>
      </div>
    </div>
  );
}
