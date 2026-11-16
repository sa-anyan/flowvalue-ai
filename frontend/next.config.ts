import type {NextConfig} from 'next';

const config: NextConfig = {
 // Isolate demo builds from the running development compiler and hot reload.
 distDir: process.env.FLOWVALUE_DEMO === '1' ? (process.env.FLOWVALUE_DEMO_OUTPUT || '.next-demo') : '.next',
};
export default config;
